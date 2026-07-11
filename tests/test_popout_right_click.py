from __future__ import annotations

import unittest
from collections.abc import Callable
from types import SimpleNamespace

from pip_monitor import PopoutWindow


class FakeWindow:
    def __init__(self) -> None:
        self.idle_callbacks: list[Callable[[], None]] = []
        self.cancelled: list[str] = []
        self.destroy_count = 0

    def after_idle(self, callback: Callable[[], None]) -> str:
        self.idle_callbacks.append(callback)
        return f"idle-{len(self.idle_callbacks)}"

    def after_cancel(self, callback_id: str) -> None:
        self.cancelled.append(callback_id)

    def destroy(self) -> None:
        self.destroy_count += 1


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


class PopoutRightClickTests(unittest.TestCase):
    def make_popout(self) -> PopoutWindow:
        popout = PopoutWindow.__new__(PopoutWindow)
        popout.window = FakeWindow()
        popout.app = SimpleNamespace(root=SimpleNamespace(after_cancel=lambda _: None))
        popout.tile = SimpleNamespace(popout=popout)
        popout.thumbnail = None
        popout.after_id = None
        popout.right_click_close_id = None
        popout.closed = False
        return popout

    def test_pointer_bindings_consume_press_and_close_on_release(self) -> None:
        popout = self.make_popout()
        widget = FakeBindingWidget()

        popout.bind_pointer_events(widget)

        self.assertNotIn("<Button-3>", widget.bindings)
        self.assertIs(
            widget.bindings["<ButtonPress-3>"].__self__,
            popout,
        )
        self.assertIs(
            widget.bindings["<ButtonRelease-3>"].__self__,
            popout,
        )

    def test_right_button_press_is_consumed_without_closing(self) -> None:
        popout = self.make_popout()

        result = popout.consume_right_click(SimpleNamespace())

        self.assertEqual(result, "break")
        self.assertFalse(popout.closed)
        self.assertEqual(popout.window.destroy_count, 0)

    def test_right_button_release_closes_only_after_idle(self) -> None:
        popout = self.make_popout()

        first_result = popout.request_right_click_close(SimpleNamespace())
        second_result = popout.request_right_click_close(SimpleNamespace())

        self.assertEqual(first_result, "break")
        self.assertEqual(second_result, "break")
        self.assertFalse(popout.closed)
        self.assertEqual(len(popout.window.idle_callbacks), 1)

        popout.window.idle_callbacks[0]()

        self.assertTrue(popout.closed)
        self.assertEqual(popout.window.destroy_count, 1)
        self.assertIsNone(popout.tile.popout)

    def test_close_is_idempotent_and_cancels_pending_right_click(self) -> None:
        popout = self.make_popout()
        popout.request_right_click_close(SimpleNamespace())

        popout.close()
        popout.close()

        self.assertEqual(popout.window.cancelled, ["idle-1"])
        self.assertEqual(popout.window.destroy_count, 1)


if __name__ == "__main__":
    unittest.main()
