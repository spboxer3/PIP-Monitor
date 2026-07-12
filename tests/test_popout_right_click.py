from __future__ import annotations

import unittest
from collections.abc import Callable
from types import SimpleNamespace
from unittest.mock import patch

from pip_monitor import PopoutWindow, aspect_fit_destination


class FakeWindow:
    def __init__(self) -> None:
        self.idle_callbacks: list[Callable[[], None]] = []
        self.cancelled: list[str] = []
        self.destroy_count = 0
        self.geometries: list[str] = []
        self.configurations: list[dict[str, object]] = []
        self.lift_count = 0
        self.x = 2100
        self.y = 100
        self.width = 640
        self.height = 360

    def after_idle(self, callback: Callable[[], None]) -> str:
        self.idle_callbacks.append(callback)
        return f"idle-{len(self.idle_callbacks)}"

    def after_cancel(self, callback_id: str) -> None:
        self.cancelled.append(callback_id)

    def destroy(self) -> None:
        self.destroy_count += 1

    def update_idletasks(self) -> None:
        pass

    def winfo_id(self) -> int:
        return 123

    def winfo_x(self) -> int:
        return self.x

    def winfo_y(self) -> int:
        return self.y

    def winfo_width(self) -> int:
        return self.width

    def winfo_height(self) -> int:
        return self.height

    def geometry(self, value: str) -> None:
        self.geometries.append(value)

    def configure(self, **kwargs: object) -> None:
        self.configurations.append(kwargs)

    def lift(self) -> None:
        self.lift_count += 1


class FakeBindingWidget:
    def __init__(self) -> None:
        self.bindings: dict[str, Callable[..., object]] = {}

    def bind(
        self,
        sequence: str,
        callback: Callable[..., object],
        *,
        add: str,
    ) -> None:
        self.bindings[sequence] = callback


class PopoutPointerControlTests(unittest.TestCase):
    def make_popout(self) -> PopoutWindow:
        popout = PopoutWindow.__new__(PopoutWindow)
        popout.window = FakeWindow()
        popout.app = SimpleNamespace(root=SimpleNamespace(after_cancel=lambda _: None))
        popout.tile = SimpleNamespace(popout=popout)
        popout.thumbnail = None
        popout.after_id = None
        popout.middle_click_close_id = None
        popout.right_click_toggle_id = None
        popout.closed = False
        popout.fullscreen = False
        popout.restore_geometry = None
        popout.move_offset = None
        popout.resize_origin = None
        popout.aspect_ratio = 16 / 9
        popout.image_label = FakeWindow()
        return popout

    def test_pointer_bindings_close_on_middle_press_and_consume_right_click(self) -> None:
        popout = self.make_popout()
        widget = FakeBindingWidget()

        popout.bind_pointer_events(widget)

        self.assertNotIn("<Button-2>", widget.bindings)
        self.assertNotIn("<Button-3>", widget.bindings)
        self.assertIs(
            widget.bindings["<ButtonPress-2>"].__func__,
            PopoutWindow.request_middle_click_close,
        )
        self.assertIs(
            widget.bindings["<ButtonPress-3>"].__func__,
            PopoutWindow.consume_right_click,
        )
        self.assertIs(
            widget.bindings["<ButtonRelease-3>"].__func__,
            PopoutWindow.request_right_click_toggle,
        )

    def test_right_button_is_consumed_and_release_toggles_once(self) -> None:
        popout = self.make_popout()
        widget = FakeBindingWidget()
        popout.bind_pointer_events(widget)
        toggles: list[bool] = []
        popout.toggle_fullscreen = lambda: toggles.append(True)

        press_result = widget.bindings["<ButtonPress-3>"](SimpleNamespace())
        first_release = widget.bindings["<ButtonRelease-3>"](SimpleNamespace())
        second_release = widget.bindings["<ButtonRelease-3>"](SimpleNamespace())

        self.assertEqual(press_result, "break")
        self.assertEqual(first_release, "break")
        self.assertEqual(second_release, "break")
        self.assertFalse(popout.closed)
        self.assertEqual(len(popout.window.idle_callbacks), 1)
        self.assertEqual(popout.window.destroy_count, 0)

        popout.window.idle_callbacks[0]()

        self.assertEqual(toggles, [True])

    def test_middle_button_press_closes_only_after_event_is_consumed(self) -> None:
        popout = self.make_popout()

        first_result = popout.request_middle_click_close(SimpleNamespace())
        second_result = popout.request_middle_click_close(SimpleNamespace())

        self.assertEqual(first_result, "break")
        self.assertEqual(second_result, "break")
        self.assertFalse(popout.closed)
        self.assertEqual(len(popout.window.idle_callbacks), 1)

        popout.window.idle_callbacks[0]()

        self.assertTrue(popout.closed)
        self.assertEqual(popout.window.destroy_count, 1)
        self.assertIsNone(popout.tile.popout)

    def test_close_cancels_pending_middle_and_right_click_actions(self) -> None:
        popout = self.make_popout()
        popout.request_middle_click_close(SimpleNamespace())
        popout.request_right_click_toggle(SimpleNamespace())

        popout.close()
        popout.close()

        self.assertEqual(popout.window.cancelled, ["idle-2", "idle-1"])
        self.assertEqual(popout.window.destroy_count, 1)

    def test_fullscreen_uses_current_monitor_and_restores_original_geometry(self) -> None:
        popout = self.make_popout()
        thumbnail_updates: list[bool] = []
        popout.update_thumbnail = lambda: thumbnail_updates.append(True)

        with patch(
            "pip_monitor.get_monitor_rect_for_window",
            return_value=(1920, 0, 5360, 1440),
        ), patch(
            "pip_monitor.ensure_rect_on_available_monitor",
            side_effect=lambda rect: rect,
        ):
            popout.toggle_fullscreen()
            popout.toggle_fullscreen()

        self.assertFalse(popout.fullscreen)
        self.assertIsNone(popout.restore_geometry)
        self.assertEqual(
            popout.window.geometries,
            ["3440x1440+1920+0", "640x360+2100+100"],
        )
        self.assertEqual(popout.window.lift_count, 1)
        self.assertEqual(thumbnail_updates, [True, True])

    def test_fullscreen_destination_preserves_content_aspect_ratio(self) -> None:
        self.assertEqual(
            aspect_fit_destination(3440, 1440, 16 / 9),
            (440, 0, 3000, 1440),
        )
        self.assertEqual(
            aspect_fit_destination(1080, 1920, 16 / 9),
            (0, 656, 1080, 1264),
        )

    def test_region_close_does_not_clear_full_popout(self) -> None:
        popout = self.make_popout()
        full_popout = object()
        popout.owner_attribute = "region_popout"
        popout.tile.popout = full_popout
        popout.tile.region_popout = popout

        popout.close()

        self.assertIs(popout.tile.popout, full_popout)
        self.assertIsNone(popout.tile.region_popout)


if __name__ == "__main__":
    unittest.main()
