"""Small Android Text-to-Speech wrapper with a desktop console fallback."""

import sys


_tts_instance = None


class TTSEngine:
    """Wrap Android TextToSpeech; print text when running outside Android."""

    def __init__(self, on_ready_callback=None):
        self.tts = None
        self.ready = False
        self.initialized = False  # Backwards-compatible name.
        self._pending = None
        self._lang = "en"
        self._TextToSpeech = None
        self._Locale = None
        self._listener = None
        self.on_ready_callback = on_ready_callback
        self.is_android = (
            hasattr(sys, "getandroidapi")
            or "android" in sys.platform.lower()
        )

        if self.is_android:
            self._init_android()
        else:
            print("[TTS preview] Non-Android system detected. Console mode.")
            self.ready = True
            self.initialized = True
            if self.on_ready_callback:
                self.on_ready_callback()

    def _init_android(self):
        try:
            from jnius import autoclass, PythonJavaClass, java_method
        except Exception as exc:
            print("pyjnius unavailable:", exc)
            return

        try:
            self._TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
            self._Locale = autoclass("java.util.Locale")
            try:
                activity = autoclass("org.kivy.android.PythonActivity").mActivity
            except Exception:
                activity = autoclass(
                    "android.app.ActivityThread"
                ).currentActivityThread().getApplication()
        except Exception as exc:
            print("[TTS] Could not resolve Android context:", exc)
            return

        outer = self

        class OnInitListener(PythonJavaClass):
            __javainterfaces__ = [
                "android/speech/tts/TextToSpeech$OnInitListener"
            ]
            __javacontext__ = "app"

            @java_method("(I)V")
            def onInit(self, status):
                if status == 0:  # TextToSpeech.SUCCESS
                    outer.ready = True
                    outer.initialized = True
                    outer._apply_lang()
                    if outer.on_ready_callback:
                        outer.on_ready_callback()
                    if outer._pending:
                        text = outer._pending
                        outer._pending = None
                        outer._speak_now(text)

        self._listener = OnInitListener()
        self.tts = self._TextToSpeech(activity, self._listener)

    def _apply_lang(self):
        if not self.tts or not self._Locale:
            return
        locale = (
            self._Locale.SIMPLIFIED_CHINESE
            if self._lang == "zh"
            else self._Locale.US
        )
        try:
            self.tts.setLanguage(locale)
        except Exception:
            pass

    @staticmethod
    def _detect_lang(text):
        return "zh" if any("\u4e00" <= ch <= "\u9fff" for ch in text) else "en"

    def _speak_now(self, text):
        try:
            self.tts.speak(
                text,
                self._TextToSpeech.QUEUE_FLUSH,
                None,
                "tts1",
            )
            return True
        except Exception as exc:
            print("tts.speak error:", exc)
            return False

    def speak(self, text):
        text = (text or "").strip()
        if not text:
            return False

        lang = self._detect_lang(text)
        if lang != self._lang:
            self._lang = lang
            if self.ready:
                self._apply_lang()

        if not self.is_android:
            try:
                print("[TTS preview] ({}) {}".format(lang, text))
            except UnicodeEncodeError:
                # Some Windows terminals use an encoding that cannot display CJK.
                print("[TTS preview] ({}) {}".format(lang, text.encode("ascii", "backslashreplace").decode("ascii")))
            return True
        if not self.ready:
            self._pending = text
            return False
        return self._speak_now(text)

    def stop(self):
        if self.tts and self.ready:
            try:
                self.tts.stop()
            except Exception:
                pass

    def shutdown(self):
        if self.tts and self.ready:
            try:
                self.tts.stop()
                self.tts.shutdown()
            except Exception:
                pass
            self.tts = None
            self.ready = False
            self.initialized = False

    def set_rate(self, rate):
        if self.tts and self.ready:
            try:
                self.tts.setSpeechRate(float(rate))
            except Exception:
                pass

    def set_pitch(self, pitch):
        if self.tts and self.ready:
            try:
                self.tts.setPitch(float(pitch))
            except Exception:
                pass


# Existing imports can continue using the old class name.
AndroidTTS = TTSEngine


def get_tts(on_ready_callback=None):
    """Return the app-wide TTS engine instance."""
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = TTSEngine(on_ready_callback)
    return _tts_instance
