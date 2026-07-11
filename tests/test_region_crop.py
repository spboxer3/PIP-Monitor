from __future__ import annotations

import unittest
from types import SimpleNamespace

from pip_monitor import NormalizedCrop, PopoutWindow


class FakeThumbnail:
    def __init__(self) -> None:
        self.updates: list[tuple[tuple[int, int, int, int], dict[str, object]]] = []

    def source_size(self) -> tuple[int, int]:
        return (1600, 900)

    def update(
        self,
        destination_rect: tuple[int, int, int, int],
        **kwargs: object,
    ) -> bool:
        self.updates.append((destination_rect, kwargs))
        return True


class FakePopoutWindow:
    def winfo_width(self) -> int:
        return 640

    def winfo_height(self) -> int:
        return 360


class NormalizedCropTests(unittest.TestCase):
    def test_from_points_normalizes_reverse_drag(self) -> None:
        crop = NormalizedCrop.from_points((800, 450), (200, 90), 1000, 500)

        self.assertEqual(crop, NormalizedCrop(0.2, 0.18, 0.8, 0.9))

    def test_from_points_clamps_to_selection_bounds(self) -> None:
        crop = NormalizedCrop.from_points((-50, 20), (1200, 600), 1000, 500)

        self.assertEqual(crop, NormalizedCrop(0.0, 0.04, 1.0, 1.0))

    def test_source_rect_scales_with_source_window(self) -> None:
        crop = NormalizedCrop(0.25, 0.1, 0.75, 0.6)

        self.assertEqual(crop.source_rect(1920, 1080), (480, 108, 1440, 648))
        self.assertEqual(crop.source_rect(1280, 720), (320, 72, 960, 432))

    def test_source_rect_always_has_positive_size(self) -> None:
        crop = NormalizedCrop(0.999, 0.999, 1.0, 1.0)

        self.assertEqual(crop.source_rect(1, 1), (0, 0, 1, 1))

    def test_rejects_empty_or_invalid_crop(self) -> None:
        with self.assertRaises(ValueError):
            NormalizedCrop.from_points((10, 10), (10, 20), 100, 100)
        with self.assertRaises(ValueError):
            NormalizedCrop(0.5, 0.0, 0.5, 1.0)

    def update_popout(self, crop: NormalizedCrop | None) -> FakeThumbnail:
        thumbnail = FakeThumbnail()
        popout = PopoutWindow.__new__(PopoutWindow)
        popout.closed = False
        popout.source_crop = crop
        popout.info = SimpleNamespace(hwnd=0)
        popout.app = SimpleNamespace(
            global_running=SimpleNamespace(get=lambda: True),
        )
        popout.window = FakePopoutWindow()
        popout.ensure_thumbnail = lambda: thumbnail
        popout.schedule_next = lambda *_: None

        popout.update_thumbnail()

        return thumbnail

    def test_full_popout_keeps_existing_uncropped_update_path(self) -> None:
        thumbnail = self.update_popout(None)

        self.assertEqual(
            thumbnail.updates,
            [((0, 0, 640, 360), {"source_rect": None, "visible": False})],
        )

    def test_region_popout_passes_scaled_crop_to_dwm(self) -> None:
        thumbnail = self.update_popout(NormalizedCrop(0.25, 0.1, 0.75, 0.6))

        self.assertEqual(
            thumbnail.updates,
            [
                (
                    (0, 0, 640, 360),
                    {"source_rect": (400, 90, 1200, 540), "visible": False},
                )
            ],
        )


if __name__ == "__main__":
    unittest.main()
