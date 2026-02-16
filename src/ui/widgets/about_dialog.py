"""About dialog.

Reason: `QMessageBox` can vertically clip long rich-text content under some Linux/
Flatpak theme + font + scaling combinations. This dialog uses a scrollable
`QTextBrowser` so content is always reachable.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QLabel,
    QSizePolicy,
    QStyle,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


class AboutDialog(QDialog):
    """Scrollable About dialog with an optional config-path footer."""

    def __init__(
        self,
        *,
        parent: QWidget,
        about_html: str,
        config_path: Optional[str] = None,
        title: str = "About",
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setModal(True)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setSizeGripEnabled(True)
        self.setMinimumSize(520, 520)

        layout = QVBoxLayout(self)

        # Reserve bottom-right space for the QSizeGrip so it doesn't obscure the
        # OK button (observed on some KDE/GTK themes and scaling factors).
        base_margin = 16
        grip_px = int(self.style().pixelMetric(QStyle.PixelMetric.PM_SizeGripSize, None, self) or 0)
        # Some styles draw an oversized grip / hit-target; reserve more than the
        # nominal size-grip metric.
        reserve_px = max((grip_px * 2) + 12, 56)
        layout.setContentsMargins(base_margin, base_margin, base_margin + reserve_px, base_margin + reserve_px)
        layout.setSpacing(12)

        self._browser = QTextBrowser(self)
        self._browser.setOpenExternalLinks(True)
        self._browser.setReadOnly(True)
        self._browser.setHtml(about_html)
        self._browser.setFrameShape(QFrame.Shape.NoFrame)
        # Let the app/theme palette drive colors; transparency avoids white boxes
        # under custom dark stylesheets.
        self._browser.setStyleSheet("QTextBrowser { background: transparent; }")
        self._browser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._browser, stretch=1)

        self._config_label = QLabel(self)
        self._config_label.setWordWrap(True)
        self._config_label.setTextFormat(Qt.TextFormat.PlainText)
        self._config_label.setStyleSheet("QLabel { color: palette(mid); }")
        self._config_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self._config_label.setVisible(bool(config_path))
        if config_path:
            self._config_label.setText(f"Config: {config_path}")
        layout.addWidget(self._config_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok, parent=self)
        # Keep the button away from the bottom-right grip.
        buttons.setCenterButtons(True)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self._apply_sensible_default_size()

    def _apply_sensible_default_size(self) -> None:
        """Pick a default size that fits most screens, without exceeding them."""

        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.resize(720, 720)
            return

        available = screen.availableGeometry()
        max_w = int(available.width() * 0.90)
        max_h = int(available.height() * 0.90)

        target_w = min(720, max_w)
        target_h = min(760, max_h)

        # Avoid a comically small dialog on tiny screens.
        target_w = max(target_w, 520)
        target_h = max(target_h, 520)

        self.resize(target_w, target_h)
