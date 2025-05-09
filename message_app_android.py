import sqlite3
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.core.clipboard import Clipboard
from kivy.clock import Clock
from kivy.properties import StringProperty


# Database Helper Class
class DatabaseManager:
    def __init__(self, db_name='messages.db'):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        # Input messages database: id, message, lang, district, category, timestamp
        cursor.execute('''CREATE TABLE IF NOT EXISTS input_messages (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            message TEXT,
                            lang TEXT,
                            district TEXT,
                            category TEXT,
                            timestamp TEXT)''')
        # Translated messages database: id, message, district, category, timestamp
        cursor.execute('''CREATE TABLE IF NOT EXISTS translated_messages (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            message TEXT,
                            district TEXT,
                            category TEXT,
                            timestamp TEXT)''')
        # Pattern database: id, pattern_name, pattern_text
        cursor.execute('''CREATE TABLE IF NOT EXISTS patterns (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            pattern_name TEXT UNIQUE,
                            pattern_text TEXT)''')
        # Converted messages database: id, message, district, category, timestamp
        cursor.execute('''CREATE TABLE IF NOT EXISTS converted_messages (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            message TEXT,
                            district TEXT,
                            category TEXT,
                            timestamp TEXT)''')
        self.conn.commit()
        # Insert default example pattern if not exists
        cursor.execute("SELECT COUNT(*) FROM patterns WHERE pattern_name = ?", ("Default Pattern",))
        if cursor.fetchone()[0] == 0:
            default_pattern = (
                "🛑 *{activity} By {activist}*:-\n"
                "▪️ *Agenda:* {agenda}\n"
                "▪️ *Venue* : {venue}\n"
                "▪️ *Time* : {time}\n"
                "▪️ *Str* : {strength}"
            )
            cursor.execute("INSERT INTO patterns (pattern_name, pattern_text) VALUES (?, ?)",
                           ("Default Pattern", default_pattern))
            self.conn.commit()

    def save_input_message(self, message, lang, district, category):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor = self.conn.cursor()
        cursor.execute('''INSERT INTO input_messages (message, lang, district, category, timestamp)
                          VALUES (?, ?, ?, ?, ?)''',
                       (message, lang, district, category, timestamp))
        self.conn.commit()

    def save_translated_message(self, message, district, category):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor = self.conn.cursor()
        cursor.execute('''INSERT INTO translated_messages (message, district, category, timestamp)
                          VALUES (?, ?, ?, ?)''',
                       (message, district, category, timestamp))
        self.conn.commit()

    def save_converted_message(self, message, district, category):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor = self.conn.cursor()
        cursor.execute('''INSERT INTO converted_messages (message, district, category, timestamp)
                          VALUES (?, ?, ?, ?)''',
                       (message, district, category, timestamp))
        self.conn.commit()

    def get_patterns(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT pattern_name FROM patterns ORDER BY pattern_name ASC")
        return [row[0] for row in cursor.fetchall()]

    def get_pattern_text(self, pattern_name):
        cursor = self.conn.cursor()
        cursor.execute("SELECT pattern_text FROM patterns WHERE pattern_name = ?", (pattern_name,))
        result = cursor.fetchone()
        if result:
            return result[0]
        return ""

    def save_pattern(self, pattern_name, pattern_text):
        cursor = self.conn.cursor()
        try:
            cursor.execute("INSERT INTO patterns (pattern_name, pattern_text) VALUES (?, ?)", (pattern_name, pattern_text))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update_pattern(self, pattern_name, pattern_text):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE patterns SET pattern_text = ? WHERE pattern_name = ?", (pattern_text, pattern_name))
        self.conn.commit()

    def query_messages(self, table_name, date=None, district=None, category=None):
        cursor = self.conn.cursor()
        query = f"SELECT message, timestamp FROM {table_name} WHERE 1=1"
        params = []
        if date:
            # date format yyyy-mm-dd so filter by date prefix in timestamp string
            query += " AND timestamp LIKE ?"
            params.append(f"{date}%")
        if district:
            query += " AND district = ?"
            params.append(district)
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY timestamp DESC"
        cursor.execute(query, params)
        return cursor.fetchall()

    def close(self):
        self.conn.close()


# Translation Helper (Dummy - replace with actual translation if needed)
def translate_to_english(text, lang):
    # For simplicity, this function returns text as-is for English
    # For Urdu and Sindhi, you can integrate any offline translation approach here
    # For now, just return input text
    if lang.lower() == 'english':
        return text
    elif lang.lower() in ('urdu', 'sindhi'):
        # Here place your translation engine or logic. Dummy returns original text
        return text
    else:
        return text


# Parsing Input for Extracting District and Category (Example logic; adjust per your real parsing needs)
def parse_area_category(text):
    # Dummy logic: extract district and category from text by keyword matching
    # A more robust approach may use NLP or regex extraction from text
    district = "Unknown"
    category = "Others"

    # Example fake logic: look for district keywords (in a real app, replace with real district names)
    known_districts = ["Hyd", "Karachi", "Lahore", "Islamabad", "Multan"]
    for d in known_districts:
        if d.lower() in text.lower():
            district = d
            break

    # Category example rules based on keywords in text (adjust as per real categories)
    if "labour" in text.lower():
        category = "A"
    elif "rally" in text.lower() or "protest" in text.lower():
        category = "B"
    elif "meeting" in text.lower():
        category = "C"
    else:
        category = "Others"

    return district, category


# Message Conversion Helper: Replace placeholders in pattern by extracting info from input text
def convert_message_to_pattern(input_text, pattern_text):
    # Basic extraction logic: identify fields by keywords in input text
    # A real app would require more advanced parsing or user entry of relevant fields

    # Here, the keys and default values of the example pattern from your description:
    data = {
        "activity": "Activity",
        "activist": "Activist",
        "agenda": "Agenda not provided",
        "venue": "Venue not specified",
        "time": "Time not specified",
        "strength": "0"
    }

    lines = input_text.splitlines()
    for line in lines:
        l = line.lower()
        if "labour day rally" in l or "activity" in l:
            data["activity"] = line.strip()
        if "by" in l and "*" not in line:
            data["activist"] = line.strip()
        if "agenda" in l:
            data["agenda"] = line.split(":", 1)[-1].strip() if ":" in line else line.strip()
        if "venue" in l:
            data["venue"] = line.split(":", 1)[-1].strip() if ":" in line else line.strip()
        if "time" in l:
            data["time"] = line.split(":", 1)[-1].strip() if ":" in line else line.strip()
        if "str" in l or "strength" in l:
            data["strength"] = line.split(":", 1)[-1].strip() if ":" in line else line.strip()

    # Format pattern by replacing placeholders
    try:
        formatted_text = pattern_text.format(**data)
    except Exception:
        formatted_text = input_text  # fallback to original input if format fails

    return formatted_text


class MessageAppGUI(BoxLayout):
    filter_date = StringProperty("")
    filter_district = StringProperty("")
    filter_category = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.db = DatabaseManager()

        # Top: Language, District, Category selectors
        top_layout = BoxLayout(size_hint_y=None, height=40, spacing=5)

        self.lang_spinner = Spinner(
            text='English',
            values=['English', 'Urdu', 'Sindhi'],
            size_hint=(0.3, None),
            height=30
        )
        top_layout.add_widget(self.lang_spinner)

        self.district_spinner = Spinner(
            text='Select District',
            values=['Unknown', 'Hyd', 'Karachi', 'Lahore', 'Islamabad', 'Multan'],
            size_hint=(0.3, None),
            height=30
        )
        top_layout.add_widget(self.district_spinner)

        self.category_spinner = Spinner(
            text='Others',
            values=['A', 'B', 'C', 'D', 'Others'],
            size_hint=(0.3, None),
            height=30
        )
        top_layout.add_widget(self.category_spinner)

        self.add_widget(top_layout)

        # Input text area (multiline)
        self.input_text = TextInput(
            hint_text='Enter or paste your message here (English, Urdu, Sindhi)...',
            multiline=True,
            size_hint_y=0.25,
            font_size=16
        )
        self.add_widget(self.input_text)

        # Pattern selection spinner
        pattern_layout = BoxLayout(size_hint_y=None, height=40, spacing=5)
        self.pattern_spinner = Spinner(
            text='Default Pattern',
            values=self.db.get_patterns(),
            size_hint=(0.6, None),
            height=30
        )
        pattern_layout.add_widget(Label(text='Select Pattern:', size_hint_x=0.2))
        pattern_layout.add_widget(self.pattern_spinner)

        # Button to edit/save pattern
        edit_pattern_btn = Button(text='Edit Pattern', size_hint_x=0.2)
        edit_pattern_btn.bind(on_release=self.edit_pattern_popup)
        pattern_layout.add_widget(edit_pattern_btn)

        self.add_widget(pattern_layout)

        # Convert message button
        convert_btn = Button(text='Convert Message', size_hint_y=None, height=40)
        convert_btn.bind(on_release=self.convert_message)
        self.add_widget(convert_btn)

        # Output text area with copy and share buttons container
        output_container = BoxLayout(orientation='vertical', size_hint_y=0.35)

        self.output_text = TextInput(
            hint_text="Converted message will appear here...",
            multiline=True,
            readonly=True,
            font_size=16
        )
        output_container.add_widget(self.output_text)

        btn_layout = BoxLayout(size_hint_y=None, height=40, spacing=5)
        copy_btn = Button(text='Copy Output')
        copy_btn.bind(on_release=self.copy_output_text)
        btn_layout.add_widget(copy_btn)

        clear_btn = Button(text='Clear')
        clear_btn.bind(on_release=self.clear_input_output)
        btn_layout.add_widget(clear_btn)

        output_container.add_widget(btn_layout)

        self.add_widget(output_container)

        # Message Logs Section with filtering (date, district, category)
        logs_layout = BoxLayout(orientation='vertical', size_hint_y=0.35, padding=5, spacing=5)

        # Filters inputs
        filter_controls = BoxLayout(size_hint_y=None, height=40, spacing=5)
        self.filter_date_input = TextInput(
            hint_text='Date: YYYY-MM-DD',
            size_hint=(0.3, None),
            height=30,
            multiline=False
        )
        filter_controls.add_widget(self.filter_date_input)

        self.filter_district_input = Spinner(
            text='All Districts',
            values=['', 'Hyd', 'Karachi', 'Lahore', 'Islamabad', 'Multan'],
            size_hint=(0.3, None),
            height=30
        )
        filter_controls.add_widget(self.filter_district_input)

        self.filter_category_input = Spinner(
            text='All Categories',
            values=['', 'A', 'B', 'C', 'D', 'Others'],
            size_hint=(0.3, None),
            height=30
        )
        filter_controls.add_widget(self.filter_category_input)

        filter_btn = Button(text='Filter Logs', size_hint=(0.1, None), height=30)
        filter_btn.bind(on_release=self.filter_logs)
        filter_controls.add_widget(filter_btn)

        logs_layout.add_widget(filter_controls)

        # Scrollable output for logs
        self.logs_output = TextInput(readonly=True, font_size=14)
        logs_layout.add_widget(self.logs_output)

        self.add_widget(logs_layout)

        # Auto-save input every 10 seconds if text changed
        self.previous_input = ''
        Clock.schedule_interval(self.autosave_input, 10)

    def convert_message(self, instance):
        input_text = self.input_text.text.strip()
        if not input_text:
            self.show_popup("Error", "Please enter a message to convert.")
            return

        # Get input details
        lang = self.lang_spinner.text
        district = self.district_spinner.text if self.district_spinner.text != "Select District" else "Unknown"
        category = self.category_spinner.text

        # Save input message
        self.db.save_input_message(input_text, lang, district, category)

        # Translate message to English
        translated = translate_to_english(input_text, lang)
        # Save translated message
        self.db.save_translated_message(translated, district, category)

        # Get selected pattern text
        pattern_name = self.pattern_spinner.text
        pattern_text = self.db.get_pattern_text(pattern_name)

        # Convert message into pattern
        converted_text = convert_message_to_pattern(translated, pattern_text)

        # Save converted message into database
        self.db.save_converted_message(converted_text, district, category)

        # Show in output box
        self.output_text.text = converted_text

        self.show_popup("Success", "Message converted and saved successfully!")

    def copy_output_text(self, instance):
        text = self.output_text.text
        if text:
            Clipboard.copy(text)
            self.show_popup("Copied", "Output text copied to clipboard.")
        else:
            self.show_popup("Error", "No text to copy.")

    def clear_input_output(self, instance):
        self.input_text.text = ''
        self.output_text.text = ''

    def edit_pattern_popup(self, instance):
        pattern_name = self.pattern_spinner.text
        pattern_text = self.db.get_pattern_text(pattern_name)

        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        pattern_input = TextInput(text=pattern_text, multiline=True, size_hint_y=0.8)
        name_input = TextInput(text=pattern_name, multiline=False, size_hint_y=0.1, readonly=True)

        content.add_widget(Label(text="Edit pattern text for:"))
        content.add_widget(name_input)
        content.add_widget(pattern_input)

        btn_layout = BoxLayout(size_hint_y=0.1, spacing=10)
        save_btn = Button(text="Save")
        cancel_btn = Button(text="Cancel")

        btn_layout.add_widget(save_btn)
        btn_layout.add_widget(cancel_btn)
        content.add_widget(btn_layout)

        popup = Popup(title="Edit Pattern", content=content, size_hint=(0.9, 0.7))

        def save_pattern(instance):
            new_text = pattern_input.text.strip()
            if len(new_text) > 0:
                self.db.update_pattern(pattern_name, new_text)
                self.show_popup("Success", "Pattern updated successfully.")
                popup.dismiss()
            else:
                self.show_popup("Error", "Pattern text cannot be empty.")

        save_btn.bind(on_release=save_pattern)
        cancel_btn.bind(on_release=lambda x: popup.dismiss())

        popup.open()

    def show_popup(self, title, message):
        popup_content = BoxLayout(orientation='vertical', padding=10)
        popup_content.add_widget(Label(text=message))
        btn = Button(text='OK', size_hint=(1, 0.3))
        popup_content.add_widget(btn)
        popup = Popup(title=title, content=popup_content, size_hint=(0.7, 0.4))
        btn.bind(on_release=popup.dismiss)
        popup.open()

    def filter_logs(self, instance):
        date = self.filter_date_input.text.strip()
        district = self.filter_district_input.text.strip() or None
        category = self.filter_category_input.text.strip() or None

        # Validate date format if set
        if date:
            try:
                datetime.strptime(date, '%Y-%m-%d')
            except ValueError:
                self.show_popup("Error", "Date format must be YYYY-MM-DD")
                return

        # Fetch logs from converted_messages table by default
        logs = self.db.query_messages('converted_messages', date=date, district=district, category=category)

        if not logs:
            self.logs_output.text = "No messages found for the given filter."
            return

        result_text = ""
        for msg, timestamp in logs:
            result_text += f"[{timestamp}] {msg}\n\n"

        self.logs_output.text = result_text.strip()

    def autosave_input(self, dt):
        current_input = self.input_text.text.strip()
        if current_input and current_input != self.previous_input:
            lang = self.lang_spinner.text
            district = self.district_spinner.text if self.district_spinner.text != "Select District" else "Unknown"
            category = self.category_spinner.text

            self.db.save_input_message(current_input, lang, district, category)
            self.previous_input = current_input

    def on_stop(self):
        self.db.close()


class MessageApp(App):
    def build(self):
        return MessageAppGUI()


if __name__ == '__main__':
    MessageApp().run()
</content>
</create_file>

<attempt_completion>
✅ Full Kivy Android app code is provided in a single Python file named `message_app_android.py`.

This app:
- Allows input of messages (English, Urdu, Sindhi).
- Lets the user select language, district, and category.
- Saves input messages with timestamp in a local SQLite DB.
- Translates (dummy pass-through for now) and stores translated messages.
- Loads and allows editing of message patterns.
- Converts input messages to formatted output messages using selected pattern.
- Saves converted messages with metadata.
- Filters and queries messages by date, district, and category.
- Provides GUI with text input/output, pattern selector, and copy/paste functionality.
- Auto-saves input message every 10 seconds if changed.
- Works fully offline with local databases.

You can run this script on Termux with Kivy installed, then package with Buildozer for Android APK.

Feel free to ask for assistance with testing, packaging, or adding advanced translation support or any other feature.
</attempt_completion>
