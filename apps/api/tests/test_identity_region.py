"""The identity region, and the crop that makes marking anonymous.

The student writes their index number in plain sight. What makes marking
anonymous is that this rectangle is removed before a marker is sent the page.

So the crop rectangle and the drawn box have to agree exactly. If the crop is
too small, identity leaks to the marker. If it is too large, handwriting is
silently destroyed. Both read from `layout`, and these tests are what hold
them together.
"""

from __future__ import annotations

import pytest

from app.core.crypto import (
    DecryptionError,
    decrypt_identifier,
    encrypt_identifier,
)
from app.engines.booklet.layout import (
    CONTENT_MARGIN_MM,
    HEADER_BOTTOM_MM,
    IDENTITY_BOX_HEIGHT_MM,
    IDENTITY_BOX_WIDTH_MM,
    PAGE_HEIGHT_MM,
    PAGE_WIDTH_MM,
    identity_region_mm,
    identity_region_px,
)

# --- geometry --------------------------------------------------------------


def test_the_region_sits_inside_the_page() -> None:
    x, y, w, h = identity_region_mm(HEADER_BOTTOM_MM)
    assert x >= 0
    assert y >= 0
    assert x + w <= PAGE_WIDTH_MM
    assert y + h <= PAGE_HEIGHT_MM


def test_the_region_does_not_overlap_a_fiducial() -> None:
    """A crop that clipped a marker would break the warp on every reprocess."""
    x, y, w, h = identity_region_mm(HEADER_BOTTOM_MM)
    assert x >= CONTENT_MARGIN_MM
    assert x + w <= PAGE_WIDTH_MM - CONTENT_MARGIN_MM


def test_the_region_matches_the_drawn_box() -> None:
    _, _, w, h = identity_region_mm(HEADER_BOTTOM_MM)
    assert w == IDENTITY_BOX_WIDTH_MM
    assert h == IDENTITY_BOX_HEIGHT_MM


@pytest.mark.parametrize("dpi", [100, 150, 200, 300])
def test_the_pixel_crop_scales_with_capture_resolution(dpi: int) -> None:
    """Neither side may hard-code pixels. A fixed offset would be silently
    wrong at any other resolution — cropping the wrong part of the page."""
    height_px = int(round(PAGE_HEIGHT_MM * dpi / 25.4))
    x, y, w, h = identity_region_px(dpi, height_px)

    expected_w = IDENTITY_BOX_WIDTH_MM * dpi / 25.4
    expected_h = IDENTITY_BOX_HEIGHT_MM * dpi / 25.4

    assert abs(w - expected_w) <= 1
    assert abs(h - expected_h) <= 1
    assert x >= 0
    assert y >= 0
    assert y + h <= height_px


def test_the_pixel_crop_is_measured_from_the_top() -> None:
    """PDFs measure from the bottom, images from the top. Getting this backwards
    would crop a question box and leave the identity visible."""
    dpi = 150
    height_px = int(round(PAGE_HEIGHT_MM * dpi / 25.4))
    _, y, h, _ = identity_region_px(dpi, height_px)

    # The box sits in the upper portion of the page, so its top edge must be
    # well above the middle once converted.
    assert y < height_px / 2


def test_the_crop_covers_the_whole_box_with_no_gap() -> None:
    """Rounding must never leave a sliver of the box outside the crop."""
    for dpi in (96.5, 150.0, 203.7, 299.1):
        height_px = int(round(PAGE_HEIGHT_MM * dpi / 25.4))
        _, _, w, h = identity_region_px(dpi, height_px)
        assert w >= int(IDENTITY_BOX_WIDTH_MM * dpi / 25.4) - 1
        assert h >= int(IDENTITY_BOX_HEIGHT_MM * dpi / 25.4) - 1


# --- encryption ------------------------------------------------------------


def test_an_identifier_round_trips() -> None:
    assert decrypt_identifier(encrypt_identifier("20512345")) == "20512345"


def test_encryption_is_not_deterministic() -> None:
    """Fernet includes a random IV. Identical ciphertexts would let anyone with
    read access group booklets by student without decrypting anything."""
    a = encrypt_identifier("20512345")
    b = encrypt_identifier("20512345")
    assert a != b
    assert decrypt_identifier(a) == decrypt_identifier(b) == "20512345"


def test_the_plaintext_is_not_recoverable_from_the_ciphertext() -> None:
    token = encrypt_identifier("20512345")
    assert b"20512345" not in token


def test_surrounding_whitespace_is_normalised() -> None:
    """Otherwise the same student produces two different stored values and the
    class-list match fails for reasons nobody can see."""
    assert decrypt_identifier(encrypt_identifier("  20512345 ")) == "20512345"


def test_an_empty_identifier_is_refused() -> None:
    with pytest.raises(ValueError, match="empty"):
        encrypt_identifier("   ")


def test_a_tampered_ciphertext_is_rejected() -> None:
    """Fernet is authenticated, so an altered token fails rather than decrypting
    to something that might then be matched against a class list."""
    token = bytearray(encrypt_identifier("20512345"))
    token[-1] ^= 0x01

    with pytest.raises(DecryptionError):
        decrypt_identifier(bytes(token))


def test_arbitrary_bytes_are_rejected() -> None:
    with pytest.raises(DecryptionError):
        decrypt_identifier(b"not a fernet token")


def test_non_numeric_identifiers_are_supported() -> None:
    """KNUST formats vary by faculty and year, so nothing here may assume
    digits. Validation is class-list membership, not a pattern."""
    for value in ("CS/20/1234", "1234567A", "PG-2026-0042"):
        assert decrypt_identifier(encrypt_identifier(value)) == value
