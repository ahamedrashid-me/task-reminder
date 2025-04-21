#!/usr/bin/env python3

import gi
import datetime
import threading
import time
import subprocess
import os

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk

class AlarmApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="Task Reminder")
        self.set_border_width(20)
        self.set_default_size(400, 300)

        self.alarm_time = None
        self.alarm_thread = None
        self.alarm_running = False
        self.sound_file = None
        self.memo_text = ""
        self.alarm_repeat_timer = None

        icon_path = os.path.join(os.path.dirname(__file__), "assets", "alarm.png")
        if os.path.exists(icon_path):
            self.set_icon_from_file(icon_path)

        # Layout
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)

        # Time picker
        self.timepicker = Gtk.SpinButton.new_with_range(0, 23, 1)
        self.timepicker.set_value(datetime.datetime.now().hour)
        self.minpicker = Gtk.SpinButton.new_with_range(0, 59, 1)
        self.minpicker.set_value(datetime.datetime.now().minute)

        hbox_time = Gtk.Box(spacing=10)
        hbox_time.pack_start(Gtk.Label(label="Alarm Time:"), False, False, 0)
        hbox_time.pack_start(self.timepicker, False, False, 0)
        hbox_time.pack_start(Gtk.Label(label=":"), False, False, 0)
        hbox_time.pack_start(self.minpicker, False, False, 0)
        vbox.pack_start(hbox_time, False, False, 0)

        # Memo
        self.memo_entry = Gtk.Entry()
        self.memo_entry.set_placeholder_text("Memo (e.g., Meeting at 10AM)")
        vbox.pack_start(self.memo_entry, False, False, 0)

        # Buttons
        btn_set = Gtk.Button(label="Set Alarm")
        btn_set.connect("clicked", self.set_alarm)
        vbox.pack_start(btn_set, False, False, 0)

        btn_stop = Gtk.Button(label="Stop Alarm")
        btn_stop.connect("clicked", self.stop_alarm)
        vbox.pack_start(btn_stop, False, False, 0)

        btn_exit = Gtk.Button(label="Exit")
        btn_exit.connect("clicked", self.on_exit)
        vbox.pack_start(btn_exit, False, False, 0)

        self.status = Gtk.Label(label="No alarm set.")
        self.status.set_name("status_label")
        vbox.pack_start(self.status, False, False, 10)

        self.load_css()

    def load_css(self):
        style_provider = Gtk.CssProvider()
        css = b"""
        #status_label {
            color: green;
            font-weight: bold;
        }
        GtkButton {
            background-color: #eef3ff;
            border-radius: 8px;
        }
        GtkLabel {
            color: #2e7d32;
            font-weight: bold;
        }
        GtkEntry {
            background-color: #ffffff;
            color: #37474f;
            border: 1px solid #cfd8dc;
            border-radius: 4px;
            padding: 5px;
        }
        """
        style_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

    def set_alarm(self, button):
        hour = int(self.timepicker.get_value())
        minute = int(self.minpicker.get_value())
        self.memo_text = self.memo_entry.get_text()

        now = datetime.datetime.now()
        alarm = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if alarm <= now:
            alarm += datetime.timedelta(days=1)

        self.alarm_time = alarm
        self.status.set_text(f"⏰ Alarm set for {self.alarm_time.strftime('%H:%M')} — {self.memo_text or 'No memo'}")

        if self.alarm_thread is None or not self.alarm_thread.is_alive():
            self.alarm_thread = threading.Thread(target=self.wait_for_alarm, daemon=True)
            self.alarm_thread.start()

    def wait_for_alarm(self):
        self.alarm_running = True
        while self.alarm_running and self.alarm_time:
            now = datetime.datetime.now()
            if now >= self.alarm_time:
                GLib.idle_add(self.trigger_alarm)
                break
            time.sleep(1)

    def trigger_alarm(self):
        if not self.alarm_running:
            return

        self.status.set_text(f"🔔 Alarm ringing! {self.memo_text or ''}")

        # Play sound loop
        alarm_end_time = time.time() + 120

        def alarm_sound_loop():
            while time.time() < alarm_end_time and self.alarm_running:
                self.play_alarm_sound()
                time.sleep(2)
            if self.alarm_running:
                self.status.set_text("⏸ Alarm paused, will repeat in 3 min.")
                self.alarm_repeat_timer = threading.Timer(180, self.trigger_alarm)
                self.alarm_repeat_timer.start()

        threading.Thread(target=alarm_sound_loop, daemon=True).start()
        GLib.idle_add(self.show_popup_actions)

    def show_popup_actions(self):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.NONE,
            text="⏰ Alarm Alert!"
        )
        dialog.format_secondary_text(self.memo_text or "Your alarm is ringing.")

        btn_stop = Gtk.Button(label="🔛 Stop")
        btn_stop.connect("clicked", lambda btn: self._handle_popup_action(dialog, "stop"))

        btn_new = Gtk.Button(label="🔁 Set New")
        btn_new.connect("clicked", lambda btn: self._handle_popup_action(dialog, "set_new"))

        btn_exit = Gtk.Button(label="❌ Exit")
        btn_exit.connect("clicked", lambda btn: self._handle_popup_action(dialog, "exit"))

        box = dialog.get_content_area()
        hbox = Gtk.Box(spacing=10)
        hbox.pack_start(btn_stop, True, True, 0)
        hbox.pack_start(btn_new, True, True, 0)
        hbox.pack_start(btn_exit, True, True, 0)
        box.add(hbox)

        dialog.show_all()

    def _handle_popup_action(self, dialog, action):
        dialog.destroy()
        if action == "stop":
            self.stop_alarm(None)
        elif action == "set_new":
            self.stop_alarm(None)
            self.memo_entry.set_text("")
            now = datetime.datetime.now()
            self.timepicker.set_value(now.hour)
            self.minpicker.set_value(now.minute)
            self.status.set_text("🕓 Set a new alarm.")
        elif action == "exit":
            self.on_exit(None)

    def stop_alarm(self, button):
        self.alarm_running = False
        if self.alarm_repeat_timer:
            self.alarm_repeat_timer.cancel()
        self.alarm_time = None
        self.status.set_text("Alarm stopped.")

    def on_exit(self, button):
        self.stop_alarm(None)
        Gtk.main_quit()

    def play_alarm_sound(self):
        subprocess.Popen([
            "play", "-n", "synth", "0.3", "sin", "880",
            "synth", "0.3", "sin", "988",
            "synth", "0.3", "sin", "1047",
            "synth", "0.3", "sin", "988"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# Run app
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print("This app no longer uses command-line arguments. Please run from the GUI.")
        sys.exit(1)

    from gi.repository import Gdk
    app = AlarmApp()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()

