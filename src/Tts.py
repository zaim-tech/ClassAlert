"""
Android Native Text-to-Speech Library for Flet / Python applications.
Interacts directly with the Android SDK using PyJNIus without Kivy bindings.
"""

import sys

# Global tracking variable to maintain a single engine context across your app
_tts_instance = None


class AndroidTTS:
    def __init__(self, on_ready_callback=None):
        """
        Initializes the Android Text-to-Speech Engine asynchronously.
        :param on_ready_callback: Optional function to run when the engine finishes initializing.
        """
        self.initialized = False
        self.tts = None
        self._pending_message = None
        self.on_ready_callback = on_ready_callback

        # Safely detect if the code is executing on an Android environment
        self.is_android = hasattr(sys, 'getandroidapi') or 'android' in sys.platform.lower()

        if self.is_android:
            from jnius import autoclass, PythonJavaClass, java_method

            # Step 1: Dynamically locate the running Android Context Activity
            try:
                # Flet / Standard Python-for-Android bootstrap activity location
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                current_activity = PythonActivity.mActivity
            except Exception:
                try:
                    # Alternative backend fallback context locator
                    Context = autoclass('android.app.ActivityThread').currentActivityThread().getApplication()
                    current_activity = Context
                except Exception as e:
                    print(f"[AndroidTTS] Critical: Could not resolve Android context activity. {e}")
                    current_activity = None

            # Step 2: Implement the asynchronous Java Listener interface
            class OnInitListener(PythonJavaClass):
                __javainterfaces__ = ['android/speech/tts/TextToSpeech$OnInitListener']

                def __init__(self, parent):
                    super().__init__()
                    self.parent = parent

                @java_method('(I)V')
                def onInit(self, status):
                    # Status 0 represents TextToSpeech.SUCCESS
                    if status == 0:
                        self.parent.initialized = True
                        
                        # Apply standard system language (US English)
                        Locale = autoclass('java.util.Locale')
                        self.parent.tts.setLanguage(Locale.US)
                        
                        # Trigger optional application notification hook
                        if self.parent.on_ready_callback:
                            self.parent.on_ready_callback()
                        
                        # Dispatch any speech string buffered during startup
                        if self.parent._pending_message:
                            self.parent.speak(self.parent._pending_message)
                            self.parent._pending_message = None

            # Step 3: Instantiate the Java TextToSpeech engine
            if current_activity:
                TextToSpeech = autoclass('android.speech.tts.TextToSpeech')
                self.listener = OnInitListener(self)
                self.tts = TextToSpeech(current_activity, self.listener)
            else:
                print("[AndroidTTS] Error: Engine instantiation aborted due to missing context.")
        else:
            # Local Desktop Development Fallback Mode
            print("[AndroidTTS Module] Non-Android system detected. Running in console mock mode.")
            self.initialized = True
            if self.on_ready_callback:
                self.on_ready_callback()

    def speak(self, text: str):
        """Speaks the input text string. Overwrites currently playing speech tracks."""
        if not text:
            return

        if self.is_android:
            if self.initialized and self.tts:
                # 0 = TextToSpeech.QUEUE_FLUSH (Interrupts active speech for immediate output)
                self.tts.speak(text, 0, None, "flet_tts_audio_channel")
            else:
                # Buffer the message if initialization is still working in the background
                self._pending_message = text
        else:
            print(f"[Desktop Mock Output]: {text}")

    def stop(self):
        """Immediately silences the ongoing audio stream."""
        if self.is_android and self.initialized and self.tts:
            self.tts.stop()

    def set_rate(self, rate: float):
        """Sets the audio voice tempo speed. Standard baseline speed is 1.0."""
        if self.is_android and self.initialized and self.tts:
            self.tts.setSpeechRate(float(rate))

    def set_pitch(self, pitch: float):
        """Modifies voice frequency. Standard tone pitch baseline is 1.0."""
        if self.is_android and self.initialized and self.tts:
            self.tts.setPitch(float(pitch))


def get_tts(on_ready_callback=None) -> AndroidTTS:
    """Singleton creation utility guaranteeing a unique shared TTS engine structure."""
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = AndroidTTS(on_ready_callback)
    return _tts_instance
