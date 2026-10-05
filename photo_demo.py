"""Isolated, explicitly staged photo walkthrough using the real local analyzer."""
import os
import sys
from pathlib import Path
import cv2
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QHBoxLayout
from app import Window
from vision import encode_png
import ui

PHOTOS = Path(__file__).parent / 'demo' / 'photos'
STEPS = (
    ('Reference check', 'reference.png', 'tidy', 0, 'Confirm the approved tidy scene.'),
    ('Clutter check 1', 'clutter.png', 'clutter_present', 1, 'First visible clutter observation.'),
    ('Blocked view', 'blocked.png', 'unable_to_assess', 1, 'A blocked view should preserve progress.'),
    ('Clutter check 2', 'clutter.png', 'clutter_present', 2, 'Second valid clutter observation.'),
    ('Clutter check 3', 'clutter.png', 'clutter_present', 3, 'Threshold reached: one genuine Windows reminder attempt.'),
    ('Clutter check 4', 'clutter.png', 'clutter_present', 4, 'Same unresolved episode: no repeated toast.'),
    ('Tidy again', 'reference.png', 'tidy', 0, 'A valid tidy observation should reset progress.'),
)
PREFERENCES = 'Books and plants are allowed here. Cups, dishes and loose paper should be removed.'


def isolated_root(local_app_data):
    return Path(local_app_data) / 'RoomTidyPhotoDemo'


class PhotoDemoWindow(Window):
    def __init__(self, data_root=None):
        self.guide_ready = False
        self.step_index = 0
        self.pending_step = None
        self.guide_area = None
        original = os.environ.get('LOCALAPPDATA')
        root = Path(data_root) if data_root is not None else isolated_root(original or str(Path.home()))
        os.environ['LOCALAPPDATA'] = str(root)
        try:
            super().__init__()
        finally:
            if original is None:
                os.environ.pop('LOCALAPPDATA', None)
            else:
                os.environ['LOCALAPPDATA'] = original
        self.timer.stop()
        self.preview_timer.stop()
        self.mode.setCurrentIndex(1)
        self.threshold.setValue(3)
        self.setWindowTitle('RoomTidy — SYNTHETIC PHOTO WALKTHROUGH')
        overview = self.pages.widget(0).widget().layout()
        guide, layout = ui.card()
        layout.addWidget(ui.label('SYNTHETIC PHOTO WALKTHROUGH', 'subtitle'))
        layout.addWidget(ui.label('Generated pictures • OpenCV checks + local Gemma analysis • manual staged checks. These are not elapsed hourly/minute observations or real-room accuracy evidence.', 'muted'))
        row = QHBoxLayout()
        self.guide_reference = self.photo_panel('Approved reference', PHOTOS / 'reference.png')
        self.guide_current = self.photo_panel('Current staged picture', PHOTOS / 'reference.png')
        row.addWidget(self.guide_reference)
        row.addWidget(self.guide_current)
        layout.addLayout(row)
        self.guide_text = ui.label('Click Use staged reference / Start to save the generated tidy reference and reset only this isolated photo-demo profile.')
        layout.addWidget(self.guide_text)
        self.guide_result = ui.label('Targets describe the intended demo behavior. The actual model output is shown honestly, including mismatches.', 'muted')
        layout.addWidget(self.guide_result)
        controls = QHBoxLayout()
        self.guide_start = QPushButton('Use staged reference / Start')
        self.guide_start.clicked.connect(self.start_walkthrough)
        self.guide_next = QPushButton('Next step')
        self.guide_next.clicked.connect(self.next_step)
        self.guide_reset = QPushButton('Reset demo')
        self.guide_reset.clicked.connect(self.reset_walkthrough)
        for button in (self.guide_start, self.guide_next, self.guide_reset):
            controls.addWidget(button)
        layout.addLayout(controls)
        layout.addWidget(ui.label('Dedicated local data: ' + str(self.store.data_dir), 'muted'))
        overview.insertWidget(2, guide)
        self.status.changed.connect(self.lock_controls)
        self.guide_ready = True
        self.lock_controls()

    @staticmethod
    def photo_panel(caption, path):
        panel = QLabel()
        panel.setAlignment(Qt.AlignCenter)
        panel.setMinimumSize(180, 140)
        panel.setAccessibleName(caption)
        panel.setToolTip(caption)
        pix = QPixmap(str(path))
        if not pix.isNull():
            panel.setPixmap(pix.scaled(360, 210, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            panel.setText(caption + ': picture not yet available')
        return panel

    def lock_controls(self):
        if not self.guide_ready:
            return
        allowed = {self.guide_start, self.guide_next, self.guide_reset}
        for button in self.pages.findChildren(QPushButton):
            if button not in allowed:
                button.setEnabled(False)
        for index, button in enumerate(self.nav_buttons):
            button.setEnabled(index == 0)
        for control in (self.mode, self.threshold, self.camera, self.preferences):
            control.setEnabled(False)
        self.guide_start.setEnabled(not self.busy and not self.close_requested)
        self.guide_reset.setEnabled(not self.busy and not self.close_requested)
        self.guide_next.setEnabled(bool(self.guide_area) and self.step_index < len(STEPS) and not self.busy and not self.close_requested)
        self.summary.setText('Guided synthetic photo demo')
        self.summary_detail.setText('No camera captures or automatic monitoring. Use the walkthrough controls above.')
        self.profile_summary.setText('Manual staged observations / Isolated demo history / Reminder threshold: 3')
        self.camera_state.setText('Local analysis in progress' if self.busy else 'Camera unused')

    def refresh(self):
        super().refresh()
        self.lock_controls()

    def submit(self, fn, kind):
        result = super().submit(fn, kind)
        self.lock_controls()
        return result

    def start_walkthrough(self):
        if self.busy:
            return
        try:
            reference = cv2.imread(str(PHOTOS / 'reference.png'))
            if reference is None:
                raise ValueError('Generated reference picture is missing.')
            for filename in ('clutter.png', 'blocked.png'):
                image = cv2.imread(str(PHOTOS / filename))
                if image is None or image.shape != reference.shape:
                    raise ValueError('Generated pictures must exist and share image dimensions.')
            self.epoch += 1
            self.guide_area = None
            self.step_index = 0
            self.pending_step = None
            self.store.delete_data()
            self.store.set_setting('threshold', 3)
            self.guide_area = self.store.add_area('Synthetic desk', [0, 0, 1, 1], PREFERENCES, encode_png(reference))
            self.store.set_setting('source_' + self.guide_area, [0, list(reference.shape[:2]), 'demo'])
            self.camera.setValue(0)
            self.step_index = 0
            self.pending_step = None
            self.show_current_photo(PHOTOS / 'reference.png')
            self.guide_text.setText('Ready: seven manually staged checks. Click Next step for the reference check. Each step uses the real local comparison pipeline.')
            self.guide_result.setText('Reference saved explicitly in the isolated photo-demo profile. Normal RoomTidy data was not opened.')
            self.refresh()
            ui.select_area(self, self.guide_area)
        except Exception as exc:
            self.status.setText('Photo demo could not start: ' + str(exc))
        self.lock_controls()

    def reset_walkthrough(self):
        if self.busy:
            return
        self.epoch += 1
        if self.guide_area:
            self.store.reset_episode(self.guide_area, 'demo')
        self.guide_area = None
        self.step_index = 0
        self.pending_step = None
        self.show_current_photo(PHOTOS / 'reference.png')
        self.guide_text.setText('Demo tracking reset. Click Use staged reference / Start to begin a fresh walkthrough.')
        self.guide_result.setText('Only the dedicated photo-demo tracking was reset. Generated assets remain available.')
        self.refresh()

    def show_current_photo(self, path):
        pix = QPixmap(str(path))
        if pix.isNull():
            self.guide_current.clear()
            self.guide_current.setText('Current staged picture is unavailable: ' + path.name)
        else:
            self.guide_current.setPixmap(pix.scaled(360, 210, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def next_step(self):
        if self.busy or not self.guide_area or self.step_index >= len(STEPS):
            return
        name, filename, expected, count, description = STEPS[self.step_index]
        self.pending_step = self.step_index
        self.show_current_photo(PHOTOS / filename)
        self.guide_text.setText(f'Step {self.step_index + 1}/7: {name}. {description} Target: {expected}; counter {count}.')
        self.guide_result.setText('Running local OpenCV/Gemma comparison; targets are not forced results.')
        self.start_analysis(lambda: cv2.imread(str(PHOTOS / filename)))
        self.lock_controls()

    def completed(self, message):
        step = self.pending_step
        super().completed(message)
        if step is None or not self.guide_ready or self.close_requested:
            return
        self.pending_step = None
        kind, result, error, epoch = message
        if epoch != self.epoch or kind != 'analysis':
            return
        name, filename, expected, expected_count, description = STEPS[step]
        area = next((a for a in self.store.areas('demo') if a['id'] == self.guide_area), None)
        if error:
            self.guide_result.setText('Actual result: unable to complete analysis. ' + error + ' No observation was fabricated. You may continue or restart.')
        else:
            observations = result[1]
            actual = next((o for a, o in observations if a['id'] == self.guide_area), None)
            if actual and area:
                matches = actual['status'] == expected and area['count'] == expected_count
                outcome = 'Matches this step target.' if matches else 'Does not match this step target; model result was kept.'
                self.guide_result.setText(f"Actual: {actual['status']} — {actual['evidence']}\nCounter: {area['count']}/3. {outcome}")
            else:
                self.guide_result.setText('No valid observation returned. Nothing was fabricated.')
        self.step_index = step + 1
        if self.step_index == len(STEPS):
            self.guide_text.setText('Walkthrough finished. These seven staged checks demonstrate the workflow, not elapsed time or real-room accuracy. Restart to repeat.')
        self.lock_controls()

    # Guard methods as well as controls: this walkthrough never reads a real camera.
    def toggle_preview(self): pass
    def preview_capture(self): pass
    def toggle_monitor(self): pass
    def scan(self): pass
    def capture_pending(self): pass
    def tick(self): pass
    def add_area(self): pass
    def update_reference(self): pass
    def save_preferences(self): pass
    def load_demo_reference(self): pass
    def import_demo(self): pass
    def cleaned(self, area_id=None): pass
    def snooze(self, area_id=None): pass
    def delete_data(self): pass


def main():
    application = QApplication(sys.argv)
    application.setStyle('Fusion')
    from ui_theme import apply_theme
    apply_theme(application)
    window = PhotoDemoWindow()
    window.show()
    return application.exec()


if __name__ == '__main__':
    sys.exit(main())
