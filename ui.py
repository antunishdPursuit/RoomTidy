"""Desktop presentation; camera, model and tracking rules remain in their owners."""
import time
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import (QWidget,QFrame,QLabel,QPushButton,QVBoxLayout,QHBoxLayout,QScrollArea,QStackedWidget,QSpinBox,QComboBox,QListWidget,QLineEdit,QCheckBox,QProgressBar,QGraphicsOpacityEffect,QSizePolicy,QAbstractSpinBox)
from PySide6.QtSvgWidgets import QSvgWidget
from ui_theme import TOKENS

ASSETS=Path(__file__).parent/'assets'
S=TOKENS["space_sm"];M=TOKENS["space_md"];L=TOKENS["space_lg"];XL=TOKENS["space_xl"]

class StatusLabel(QLabel):
    changed=Signal()
    def setText(self,text):
        self.setToolTip(text)
        self.setAccessibleDescription(text)
        summary=text
        if len(text)>200 or "\n" in text:
            summary=text.splitlines()[0][:160]+"... See area cards; full message is available on hover."
        super().setText(summary)
        self.changed.emit()

def label(text,kind=None):
    widget=QLabel(text);widget.setTextFormat(Qt.PlainText);widget.setWordWrap(True)
    if kind:widget.setObjectName(kind)
    return widget

def button(text,fn,role=None):
    widget=QPushButton(text);widget.clicked.connect(lambda checked=False:fn())
    if role:widget.setProperty('role',role)
    return widget

def card():
    widget=QFrame();widget.setObjectName('card');layout=QVBoxLayout(widget);layout.setContentsMargins(XL,XL,XL,XL);layout.setSpacing(M)
    return widget,layout

def page(title,subtitle):
    scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame)
    content=QWidget();content.setObjectName("pageContent");scroll.setObjectName("page");layout=QVBoxLayout(content);layout.setContentsMargins(XL,XL,XL,XL);layout.setSpacing(L)
    layout.addWidget(label(title,'title'));layout.addWidget(label(subtitle,'muted'));scroll.setWidget(content)
    return scroll,layout

def build(w,Preview):
    root=QWidget();w.setCentralWidget(root);outer=QHBoxLayout(root);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0)
    nav=QFrame();nav.setObjectName('sidebar');nav.setFixedWidth(170);sidebar=QVBoxLayout(nav);sidebar.setContentsMargins(L,XL,L,XL);sidebar.setSpacing(S)
    sidebar.addWidget(label('RoomTidy','subtitle'));sidebar.addWidget(label('A little space to reset.','muted'));sidebar.addSpacing(XL)
    w.pages=QStackedWidget();w.nav_buttons=[]
    for index,text in enumerate(['Overview','Camera setup','Settings','How to use']):
        b=button(text,lambda i=index:navigate(w,i),'nav');b.setCheckable(True);sidebar.addWidget(b);w.nav_buttons.append(b)
    sidebar.addStretch();sidebar.addWidget(label('Local Gemma 4','muted'));w.camera_state=label('Camera idle','muted');sidebar.addWidget(w.camera_state)
    outer.addWidget(nav);outer.addWidget(w.pages,1)
    overview,layout=page('Your room, at a glance','Gentle reminders for the areas you choose.')
    f,l=card();w.summary=label('Monitoring is paused','subtitle');l.addWidget(w.summary)
    w.summary_detail=label('Save a tidy reference to get started.','muted');l.addWidget(w.summary_detail)
    controls=QHBoxLayout();w.monitor=button('Resume monitoring',w.toggle_monitor,'primary');controls.addWidget(w.monitor)
    w.check_button=button('Check now',w.scan);controls.addWidget(w.check_button);controls.addStretch();l.addLayout(controls)
    w.profile_summary=label('Live mode / Hourly checks / 30 valid checks','muted');l.addWidget(w.profile_summary);layout.addWidget(f)
    heading=QHBoxLayout();heading.addWidget(label('Your areas','subtitle'));heading.addStretch();heading.addWidget(button('Manage areas',lambda:navigate(w,1)));layout.addLayout(heading)
    w.card_container=QWidget();w.card_layout=QVBoxLayout(w.card_container);w.card_layout.setContentsMargins(0,0,0,0);w.card_layout.setSpacing(L);layout.addWidget(w.card_container)
    w.empty_card,w.empty_layout=card();illustration=QSvgWidget(str(ASSETS/'room-illustration.svg'));illustration.setFixedSize(250,150);w.empty_layout.addWidget(illustration,0,Qt.AlignCenter)
    w.empty_layout.addWidget(label('Make space for a fresh start','subtitle'));w.empty_layout.addWidget(label('First, tidy one area the way you like it. Then save a camera reference so RoomTidy knows what to compare.','muted'))
    w.empty_layout.addWidget(button('Set up your first area',lambda:navigate(w,1),'primary'));layout.addWidget(w.empty_card)
    layout.addStretch();layout.addWidget(label('Dark, blocked or missed checks do not advance the counter. Closing this window stops monitoring.','muted'));w.pages.addWidget(overview)

    setup,layout=page('Camera setup','Save what tidy means to you. Keep the camera in the same position afterward.')
    f,l=card();l.addWidget(label('1. Tidy the area and open the camera','subtitle'));l.addWidget(label('The saved picture is your comparison reference. RoomTidy never replaces it automatically.','muted'))
    row=QHBoxLayout();w.camera=QSpinBox();w.camera.setButtonSymbols(QAbstractSpinBox.PlusMinus);w.camera.setRange(0,9);w.camera.setPrefix('Camera ');w.camera.setValue(w.store.get_setting('camera',0));w.camera.valueChanged.connect(w.camera_changed);row.addWidget(w.camera)
    w.preview_button=button('Open / close preview',w.toggle_preview);row.addWidget(w.preview_button);row.addStretch();l.addLayout(row)
    w.preview=Preview();w.preview.setMinimumSize(100,240);w.preview.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding);l.addWidget(w.preview);layout.addWidget(f)
    f,l=card();l.addWidget(label('2. Drag an area, then save its tidy reference','subtitle'));l.addWidget(label('Drag a rectangle on the preview around your desk or floor. Describe allowed items below, click Save tidy reference, and give the area a name.','muted'))
    l.addWidget(label('Area preferences'));w.preferences=QLineEdit();w.preferences.setPlaceholderText('Books are allowed here; dishes should be removed.');w.preferences.setAccessibleName('Area preferences');l.addWidget(w.preferences)
    row=QHBoxLayout();w.add_button=button('Save tidy reference',w.add_area,'primary');row.addWidget(w.add_button);row.addStretch();l.addLayout(row)
    l.addWidget(label('Changing an existing reference or preferences resets both live and demo tracking for that area, after confirmation.','muted'));layout.addWidget(f)
    f,l=card();l.addWidget(label('3. Review saved areas','subtitle'));w.areas=QListWidget();w.areas.setMinimumHeight(100);w.areas.setMaximumHeight(180);w.areas.setAccessibleName('Saved areas');w.areas.currentItemChanged.connect(w.load_preferences);l.addWidget(w.areas)
    w.reference_view=label('Select an area to view its saved tidy reference.','muted');w.reference_view.setMaximumHeight(130);l.addWidget(w.reference_view)
    row=QHBoxLayout();w.update_button=button('Update tidy reference',w.update_reference);row.addWidget(w.update_button);w.preferences_button=button('Save preferences',w.save_preferences);row.addWidget(w.preferences_button);l.addLayout(row)
    l.addWidget(button('Go to monitoring',lambda:navigate(w,0),'primary'));layout.addWidget(f);layout.addStretch();w.pages.addWidget(setup)

    settings,layout=page('Settings','Choose live monitoring or a clearly labelled demo. All data stays on this computer.')
    f,l=card();l.addWidget(label('Monitoring profile','subtitle'));l.addWidget(label('Live checks run hourly. Demo checks run every minute. Invalid checks do not count. In Demo, 30 valid checks can take longer than 30 minutes; Live checks are hourly.','muted'))
    w.mode=QComboBox();w.mode.addItems(['Live: hourly','Demo: every minute']);w.mode.currentIndexChanged.connect(w.change_mode);l.addWidget(w.mode)
    l.addWidget(label('Valid clutter checks before a reminder'));w.threshold=QSpinBox();w.threshold.setButtonSymbols(QAbstractSpinBox.PlusMinus);w.threshold.setRange(1,1000);w.threshold.setValue(int(w.store.get_setting('threshold',30)));w.threshold.valueChanged.connect(w.threshold_changed);l.addWidget(w.threshold)
    l.addWidget(label('Use 30 for normal monitoring. A threshold of 3 makes a short demo. Demo progress is separate. References, preferences and this threshold are shared; set the threshold back to 30 when returning to Live.','muted'));layout.addWidget(f)
    f,l=card();l.addWidget(label('Demo pictures','subtitle'));l.addWidget(label('Use the included synthetic pictures to demonstrate the workflow. These are not real-room accuracy tests.','muted'))
    w.demo_reference_button=button('Load demo reference picture',lambda:demo_reference(w));l.addWidget(w.demo_reference_button);w.demo_import_button=button('Import demo picture',w.import_demo);l.addWidget(w.demo_import_button);layout.addWidget(f)
    f,l=card();l.addWidget(label('Appearance','subtitle'));w.reduce_motion=QCheckBox('Reduce motion');w.reduce_motion.setChecked(bool(w.store.get_setting('reduce_motion',False)));w.reduce_motion.toggled.connect(lambda checked:motion_changed(w,checked));l.addWidget(w.reduce_motion);layout.addWidget(f)
    f,l=card();l.addWidget(label('Local data','subtitle'));l.addWidget(label('Only tidy reference pictures and up to 500 observation metadata entries are stored. Routine camera images stay in memory. Desktop reminders may appear on your lock screen.','muted'))
    l.addWidget(button('Delete local app data',w.delete_data,'danger'));layout.addWidget(f);layout.addStretch();w.pages.addWidget(settings)

    help_page,layout=page('How to use RoomTidy','The app compares selected areas with pictures you explicitly approve as tidy.')
    for title,text in [
        ('1. Set your reference','Tidy your chosen area first. In Camera setup, open the preview, drag a rectangle, enter preferences, and save its tidy reference with a name.'),
        ('2. Start monitoring','Go to Overview and press Resume monitoring. Keep RoomTidy open and the computer awake. The camera shows a notice before each snapshot, then releases. Live checks run hourly; Check now gives an immediate assessment.'),
        ('3. Read the results','Clutter observed adds one valid check. Matches reference clears the counter. Unable to assess preserves progress. Live clutter counts advance at most hourly, even with repeated manual checks. Thirty checks is not proof of thirty continuous hours.'),
        ('4. Respond to reminders','At the threshold, RoomTidy attempts one Windows notification for the unresolved condition. Cleaned resets progress without replacing the reference. Snooze hides the reminder for one hour; it does not repeat the same toast.'),
        ('5. Try a quick demo','In Settings choose Demo and set the threshold to 3. Load demo/tidy.png as the reference picture, select nearly the whole image, and save an area. Use preferences: Red square is allowed; blue circular objects should be removed. Import demo/clutter.png three times. Dark and blocked pictures should leave the counter unchanged; tidy clears it.'),
        ('Camera or lighting trouble','Keep the camera fixed and the area visible. Brightness checks catch dark or blank views; textured obstructions and camera movement can still confuse the model. If you move the camera, explicitly capture a new reference. If analysis times out, pause and try again when GPU load is lower.')]:
        f,l=card();l.addWidget(label(title,'subtitle'));l.addWidget(label(text,'muted'));layout.addWidget(f)
    layout.addStretch();w.pages.addWidget(help_page)
    footer=QFrame();footer.setObjectName('statusBar');footer_layout=QVBoxLayout(footer);footer_layout.setContentsMargins(24,12,24,12)
    w.status=StatusLabel('Paused. Set up an area and save its tidy reference first.');w.status.setTextFormat(Qt.PlainText);w.status.setWordWrap(True);w.status.setObjectName('status');w.status.setMaximumHeight(100);w.status.setAccessibleName('Current operation status');footer_layout.addWidget(w.status)
    wrapper=QWidget();vertical=QVBoxLayout(wrapper);vertical.setContentsMargins(0,0,0,0);vertical.setSpacing(0)
    outer.removeWidget(w.pages);vertical.addWidget(w.pages,1);vertical.addWidget(footer);outer.addWidget(wrapper,1)
    w.status.changed.connect(lambda:sync(w));w._page_animation=None;w._animated_page=None
    w.nav_buttons[0].setChecked(True);sync(w)

def navigate(w,index):
    if w.pages.currentIndex()==1 and index!=1 and w.previewing:w.toggle_preview()
    if w._page_animation:
        w._page_animation.stop();w._page_animation.deleteLater()
        if w._animated_page:w._animated_page.setGraphicsEffect(None)
        w._page_animation=None
    w.pages.setCurrentIndex(index)
    for i,b in enumerate(w.nav_buttons):b.setChecked(i==index)
    if not w.reduce_motion.isChecked():
        target=w.pages.currentWidget();effect=QGraphicsOpacityEffect(target);target.setGraphicsEffect(effect)
        animation=QPropertyAnimation(effect,b'opacity',w);animation.setDuration(160);animation.setStartValue(.35);animation.setEndValue(1.0);animation.setEasingCurve(QEasingCurve.OutCubic)
        w._page_animation=animation;w._animated_page=target
        animation.finished.connect(lambda:finish_animation(w,animation,target));animation.start()

def finish_animation(w,animation,target):
    if w._page_animation is animation:
        target.setGraphicsEffect(None);w._page_animation=None;w._animated_page=None
    animation.deleteLater()

def motion_changed(w,checked):
    w.store.set_setting('reduce_motion',bool(checked))
    if checked and w._page_animation:
        w._page_animation.stop();w._page_animation.deleteLater();w._page_animation=None
        if w._animated_page:w._animated_page.setGraphicsEffect(None)
        w._animated_page=None

def demo_reference(w):
    navigate(w,1);w.load_demo_reference()

def select_area(w,area_id):
    for index in range(w.areas.count()):
        if w.areas.item(index).data(Qt.UserRole)==area_id:w.areas.setCurrentRow(index);return

def area_action(w,area_id,action):
    if action=='reference':select_area(w,area_id);w.load_preferences();navigate(w,1)
    elif action=='cleaned':w.cleaned(area_id)
    else:w.snooze(area_id)

def render(w):
    while w.card_layout.count():
        item=w.card_layout.takeAt(0)
        if item.widget():item.widget().deleteLater()
    areas=w.store.areas(w.mode_name());latest={}
    for observation in w.store.history(w.mode_name()):latest.setdefault(observation['area_id'],observation)
    w.empty_card.setVisible(not areas)
    for area in areas:
        f,l=card();header=QHBoxLayout();header.addWidget(label(area['name'],'subtitle'));header.addStretch()
        reminder='Snoozed until '+time.strftime('%H:%M',time.localtime(area['snooze_until'])) if area['snooze_until']>time.time() else ('Reminder active' if area['alerted'] else 'Tracking')
        header.addWidget(label(reminder,'muted'));l.addLayout(header)
        record=latest.get(area['id'])
        if record:
            state={'tidy':'Matches reference','clutter_present':'Clutter observed','unable_to_assess':'Unable to assess'}[record['status']]
            l.addWidget(label('Last recorded check: '+state+' / '+time.strftime('%b %d, %H:%M',time.localtime(record['observed_at'])),'muted'))
            l.addWidget(label('Model-reported observation: '+record['evidence']))
        else:l.addWidget(label('Reference saved. No model observations yet.','muted'))
        progress=QProgressBar();progress.setRange(0,w.threshold.value());progress.setValue(min(area['count'],w.threshold.value()));progress.setTextVisible(False);l.addWidget(progress)
        l.addWidget(label(f"{area['count']} of {w.threshold.value()} valid clutter checks",'muted'))
        row=QHBoxLayout()
        for text,action in [('View reference','reference'),('Cleaned','cleaned'),('Snooze 1 hour','snooze')]:
            row.addWidget(button(text,lambda aid=area['id'],act=action:area_action(w,aid,act)))
        row.addStretch();l.addLayout(row);w.card_layout.addWidget(f)
    sync(w)

def sync(w):
    areas=w.store.areas(w.mode_name());has_areas=bool(areas)
    w.summary.setText('Monitoring is enabled' if w.enabled else 'Monitoring is paused')
    w.summary_detail.setText('A snapshot notice appears before each check. Keep the app open and the computer awake.' if w.enabled else ('Automatic checks are off. Manual Check now is available.' if has_areas else 'Start in Camera setup: select an area and save its tidy reference.'))
    profile='DEMO / Every minute' if w.mode_name()=='demo' else 'Live / Hourly checks'
    w.profile_summary.setText(f'{profile} / Reminder at {w.threshold.value()} valid clutter checks')
    w.camera_state.setText('Preview active' if w.previewing else ('Local work in progress' if w.busy else 'Camera idle'))
    w.monitor.setEnabled(has_areas and not w.close_requested)
    w.check_button.setEnabled(has_areas and not w.busy and w.pending is None and not w.close_requested)
    w.preview_button.setText('Close preview' if w.previewing else 'Open preview')
    w.preview_button.setEnabled(not w.close_requested)
    w.add_button.setEnabled(w.preview.frame is not None and w.frame_kind in ('camera','demo') and not w.close_requested)
    w.update_button.setEnabled(w.selected() is not None and w.preview.frame is not None and w.frame_kind in ('camera','demo'))
    w.preferences_button.setEnabled(w.selected() is not None)
    w.demo_reference_button.setEnabled(w.mode_name()=='demo' and not w.busy)
    w.demo_import_button.setEnabled(w.mode_name()=='demo' and has_areas and not w.busy)
