from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from emerlang import Codebook
from emerlang.encoder import encode as em_encode
from emerlang.decoder import decode as em_decode

ENCODINGS = ("utf-8", "utf-8-sig", "utf-16-le", "utf-16-be")


def read_text_any(path: str) -> str:
    b = Path(path).read_bytes()
    for enc in ENCODINGS:
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode("utf-8", errors="replace")


# ----------------------------- Build Tab -----------------------------
class BuildTab(QtWidgets.QWidget):
    built = QtCore.Signal(str)  # emits codebook path

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._wire()

        # Default the corpus to examples\\corpora\\mini_en.txt (project root if possible)
        # Falls back gracefully if not found.
        try:
            # when running from source tree: .../src/emerlang/gui/emerlang_gui.py
            proj_root = Path(__file__).resolve().parents[3]
            default_corpus = proj_root / "examples" / "corpora" / "mini_en.txt"
        except Exception:
            default_corpus = Path("examples") / "corpora" / "mini_en.txt"

        if default_corpus.exists():
            self.corpusPath.setText(str(default_corpus))

    def _init_ui(self):
        self.corpusPath = QtWidgets.QLineEdit()
        self.corpusBrowse = QtWidgets.QPushButton("Browse…")
        self.outputPath = QtWidgets.QLineEdit("codebook.json")
        self.outputBrowse = QtWidgets.QPushButton("Save As…")
        self.vocab = QtWidgets.QSpinBox(); self.vocab.setRange(50, 10000); self.vocab.setValue(300)
        self.seed = QtWidgets.QSpinBox(); self.seed.setRange(0, 2**31-1); self.seed.setValue(42)

        # Build button (green with white text)
        self.buildBtn = QtWidgets.QPushButton("Build codebook")
        self.buildBtn.setEnabled(False)
        self.buildBtn.setStyleSheet(
            "QPushButton { background-color: #16a34a; color: white; font-weight: 600; padding: 6px 12px; border-radius: 6px; }"
            "QPushButton:disabled { background-color: #9ca3af; color: white; }"
            "QPushButton:hover:!disabled { background-color: #15803d; }"
        )

        self.analyzeBtn = QtWidgets.QPushButton("Analyze")

        self.preview = QtWidgets.QPlainTextEdit(); self.preview.setReadOnly(True); self.preview.setPlaceholderText("Corpus preview…")
        self.tokensTable = QtWidgets.QTableWidget(0, 3)
        self.tokensTable.setHorizontalHeaderLabels(["Word", "Freq", "Mapped?"])
        self.tokensTable.horizontalHeader().setStretchLastSection(True)
        self.tokensTable.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.tokensTable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.meta = QtWidgets.QLabel("—")
        self.progress = QtWidgets.QProgressBar(); self.progress.setRange(0, 0); self.progress.hide()
        self.status = QtWidgets.QLabel("")

        grid = QtWidgets.QGridLayout()
        grid.addWidget(QtWidgets.QLabel("Corpus"), 0, 0)
        grid.addWidget(self.corpusPath, 0, 1)
        grid.addWidget(self.corpusBrowse, 0, 2)
        grid.addWidget(QtWidgets.QLabel("Output"), 1, 0)
        grid.addWidget(self.outputPath, 1, 1)
        grid.addWidget(self.outputBrowse, 1, 2)

        opt = QtWidgets.QHBoxLayout()
        opt.addWidget(QtWidgets.QLabel("Vocab")); opt.addWidget(self.vocab)
        opt.addWidget(QtWidgets.QLabel("Seed")); opt.addWidget(self.seed)
        opt.addStretch(1)

        btns = QtWidgets.QHBoxLayout()
        btns.addWidget(self.analyzeBtn); btns.addStretch(1); btns.addWidget(self.buildBtn)

        splitter = QtWidgets.QSplitter()
        left = QtWidgets.QWidget(); llay = QtWidgets.QVBoxLayout(left); llay.addWidget(QtWidgets.QLabel("Preview")); llay.addWidget(self.preview)
        right = QtWidgets.QWidget(); rlay = QtWidgets.QVBoxLayout(right); rlay.addWidget(QtWidgets.QLabel("Top tokens")); rlay.addWidget(self.tokensTable)
        splitter.addWidget(left); splitter.addWidget(right); splitter.setStretchFactor(0, 1); splitter.setStretchFactor(1, 1)

        v = QtWidgets.QVBoxLayout(self)
        v.addLayout(grid); v.addLayout(opt); v.addLayout(btns)
        v.addWidget(splitter, 1)
        v.addWidget(self.meta); v.addWidget(self.progress); v.addWidget(self.status)

    def _wire(self):
        self.corpusBrowse.clicked.connect(self._pick_corpus)
        self.outputBrowse.clicked.connect(self._pick_output)
        self.analyzeBtn.clicked.connect(self._analyze)
        self.buildBtn.clicked.connect(self._build)
        self.corpusPath.textChanged.connect(self._on_path_changed)

    def _pick_corpus(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose corpus", "", "Text files (*.txt *.md);;All files (*.*)")
        if p: self.corpusPath.setText(p)

    def _pick_output(self):
        p, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save codebook", "codebook.json", "JSON (*.json)")
        if p: self.outputPath.setText(p)

    def _on_path_changed(self, _):
        ok = Path(self.corpusPath.text()).exists()
        self.buildBtn.setEnabled(ok)
        if ok:
            try:
                text = read_text_any(self.corpusPath.text())
                self.preview.setPlainText(text[:2048])
                if not self.outputPath.text().strip():
                    out = str(Path(self.corpusPath.text()).with_name("codebook.json"))
                    self.outputPath.setText(out)
                self.status.setText("")
            except Exception as e:
                self.preview.setPlainText("")
                self.status.setText(f"Failed to read corpus: {e}")

    def _analyze(self):
        try:
            text = read_text_any(self.corpusPath.text())
            import re, collections
            WORD_RE = re.compile(r"[^\W\d_]+(?:['’\\-][^\W\d_]+)*|[0-9]+", re.UNICODE)
            toks = WORD_RE.findall(text)
            words = [t.lower() for t in toks]
            freq = collections.Counter(words)
            top = freq.most_common(50)
            self.tokensTable.setRowCount(len(top))
            for i, (w, c) in enumerate(top):
                self.tokensTable.setItem(i, 0, QtWidgets.QTableWidgetItem(w))
                self.tokensTable.setItem(i, 1, QtWidgets.QTableWidgetItem(str(c)))
                self.tokensTable.setItem(i, 2, QtWidgets.QTableWidgetItem("✓" if i < self.vocab.value() else "–"))
            self.status.setText(f"Analyzed {len(words)} tokens; showing top {len(top)}.")
        except Exception as e:
            self.status.setText(f"Analyze failed: {e}")

    def _build(self):
        corpus = self.corpusPath.text().strip()
        out = self.outputPath.text().strip()
        if not corpus or not Path(corpus).exists():
            self.status.setText("Select a valid corpus file."); return
        if not out:
            self.status.setText("Choose an output path."); return
        if Path(out).exists():
            r = QtWidgets.QMessageBox.question(self, "Overwrite?", f"{out} exists. Overwrite?")
            if r != QtWidgets.QMessageBox.Yes: return
        self.progress.show(); self.status.setText("Building…")
        QtWidgets.QApplication.processEvents()
        try:
            cb = Codebook.train(corpus_path=corpus, vocab_size=self.vocab.value(), seed=self.seed.value())
            cb.save(out)
            self.progress.hide()
            self.meta.setText(f"Saved: {out}  •  vocab={self.vocab.value()}  •  seed={self.seed.value()}")
            self.status.setText("Build complete.")
            self.built.emit(out)
        except Exception as e:
            self.progress.hide()
            self.status.setText(f"Build failed: {e}")


# ----------------------------- Encode Tab -----------------------------
class EncodeTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui(); self._wire()

    def _init_ui(self):
        self.codebookPath = QtWidgets.QLineEdit("codebook.json")
        self.codebookBrowse = QtWidgets.QPushButton("Browse…")
        self.inFile = QtWidgets.QLineEdit("")
        self.inBrowse = QtWidgets.QPushButton("Open…")
        self.outFile = QtWidgets.QLineEdit("out.em")
        self.outBrowse = QtWidgets.QPushButton("Save As…")
        self.structure = QtWidgets.QSlider(QtCore.Qt.Horizontal); self.structure.setRange(0, 100); self.structure.setValue(20)
        self.structLabel = QtWidgets.QLabel("Structure: 0.20")
        self.seed = QtWidgets.QSpinBox(); self.seed.setRange(0, 2**31-1); self.seed.setValue(42)

        self.textIn = QtWidgets.QPlainTextEdit(); self.textIn.setPlaceholderText("Input text (or choose a file above)…")
        self.textOut = QtWidgets.QPlainTextEdit(); self.textOut.setPlaceholderText("Encoded output…"); self.textOut.setReadOnly(True)

        # Encode button (blue with white text)
        self.runBtn = QtWidgets.QPushButton("Encode")
        self.runBtn.setStyleSheet(
            "QPushButton { background-color: #2563eb; color: white; font-weight: 600; padding: 6px 12px; border-radius: 6px; }"
            "QPushButton:hover { background-color: #1d4ed8; }"
        )

        grid = QtWidgets.QGridLayout()
        grid.addWidget(QtWidgets.QLabel("Codebook"), 0, 0); grid.addWidget(self.codebookPath, 0, 1); grid.addWidget(self.codebookBrowse, 0, 2)
        grid.addWidget(QtWidgets.QLabel("Input file"), 1, 0); grid.addWidget(self.inFile, 1, 1); grid.addWidget(self.inBrowse, 1, 2)
        grid.addWidget(QtWidgets.QLabel("Output file"), 2, 0); grid.addWidget(self.outFile, 2, 1); grid.addWidget(self.outBrowse, 2, 2)

        opts = QtWidgets.QHBoxLayout()
        opts.addWidget(self.structLabel); opts.addWidget(self.structure); opts.addSpacing(12)
        opts.addWidget(QtWidgets.QLabel("Seed")); opts.addWidget(self.seed); opts.addStretch(1); opts.addWidget(self.runBtn)

        split = QtWidgets.QSplitter(); split.setOrientation(QtCore.Qt.Vertical)
        w1 = QtWidgets.QWidget(); l1 = QtWidgets.QVBoxLayout(w1); l1.addWidget(QtWidgets.QLabel("Text input")); l1.addWidget(self.textIn)
        w2 = QtWidgets.QWidget(); l2 = QtWidgets.QVBoxLayout(w2); l2.addWidget(QtWidgets.QLabel("Encoded")); l2.addWidget(self.textOut)
        split.addWidget(w1); split.addWidget(w2)

        v = QtWidgets.QVBoxLayout(self)
        v.addLayout(grid); v.addLayout(opts); v.addWidget(split, 1)

    def _wire(self):
        self.codebookBrowse.clicked.connect(lambda: self._pick(self.codebookPath, "JSON (*.json)"))
        self.inBrowse.clicked.connect(lambda: self._pick(self.inFile, "Text (*.txt *.md);;All files (*.*)"))
        self.outBrowse.clicked.connect(lambda: self._save(self.outFile, "Emergent (*.em);;All files (*.*)"))
        self.structure.valueChanged.connect(lambda v: self.structLabel.setText(f"Structure: {v/100:.2f}"))
        self.runBtn.clicked.connect(self._run)

    def _pick(self, edit: QtWidgets.QLineEdit, filt: str):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open", "", filt)
        if p: edit.setText(p)

    def _save(self, edit: QtWidgets.QLineEdit, filt: str):
        p, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save As", edit.text() or "out.em", filt)
        if p: edit.setText(p)

    def _run(self):
        cb_path = self.codebookPath.text().strip()
        try:
            cb = Codebook.load(cb_path)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to load codebook: {e}"); return

        text = self.textIn.toPlainText().strip()
        if not text and self.inFile.text().strip():
            try:
                text = read_text_any(self.inFile.text().strip())
                self.textIn.setPlainText(text)
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Error", f"Failed to read input file: {e}"); return

        emergent = em_encode(text, cb, structure=self.structure.value()/100.0, seed=self.seed.value())
        self.textOut.setPlainText(emergent)

        if self.outFile.text().strip():
            try:
                Path(self.outFile.text().strip()).write_text(emergent, encoding="utf-8")
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Error", f"Failed to save output: {e}")


# ----------------------------- Decode Tab -----------------------------
class DecodeTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui(); self._wire()

    def _init_ui(self):
        self.codebookPath = QtWidgets.QLineEdit("codebook.json")
        self.codebookBrowse = QtWidgets.QPushButton("Browse…")
        self.inFile = QtWidgets.QLineEdit("")
        self.inBrowse = QtWidgets.QPushButton("Open…")
        self.outFile = QtWidgets.QLineEdit("roundtrip.txt")
        self.outBrowse = QtWidgets.QPushButton("Save As…")

        self.textIn = QtWidgets.QPlainTextEdit(); self.textIn.setPlaceholderText("Emergent text (or choose a file above)…")
        self.textOut = QtWidgets.QPlainTextEdit(); self.textOut.setPlaceholderText("Decoded output…"); self.textOut.setReadOnly(True)

        # Decode button (blue with white text) — placed right after Output file row
        self.runBtn = QtWidgets.QPushButton("Decode")
        self.runBtn.setStyleSheet(
            "QPushButton { background-color: #2563eb; color: white; font-weight: 600; padding: 6px 12px; border-radius: 6px; }"
            "QPushButton:hover { background-color: #1d4ed8; }"
        )

        grid = QtWidgets.QGridLayout()
        grid.addWidget(QtWidgets.QLabel("Codebook"), 0, 0); grid.addWidget(self.codebookPath, 0, 1); grid.addWidget(self.codebookBrowse, 0, 2)
        grid.addWidget(QtWidgets.QLabel("Input file"), 1, 0); grid.addWidget(self.inFile, 1, 1); grid.addWidget(self.inBrowse, 1, 2)
        grid.addWidget(QtWidgets.QLabel("Output file"), 2, 0); grid.addWidget(self.outFile, 2, 1); grid.addWidget(self.outBrowse, 2, 2)

        # Button row inserted here (before emergent input area)
        row_btn = QtWidgets.QHBoxLayout(); row_btn.addStretch(1); row_btn.addWidget(self.runBtn)

        split = QtWidgets.QSplitter(); split.setOrientation(QtCore.Qt.Vertical)
        w1 = QtWidgets.QWidget(); l1 = QtWidgets.QVBoxLayout(w1); l1.addWidget(QtWidgets.QLabel("Emergent input")); l1.addWidget(self.textIn)
        w2 = QtWidgets.QWidget(); l2 = QtWidgets.QVBoxLayout(w2); l2.addWidget(QtWidgets.QLabel("Decoded")); l2.addWidget(self.textOut)
        split.addWidget(w1); split.addWidget(w2)

        v = QtWidgets.QVBoxLayout(self)
        v.addLayout(grid); v.addLayout(row_btn); v.addWidget(split, 1)

    def _wire(self):
        self.codebookBrowse.clicked.connect(lambda: self._pick(self.codebookPath, "JSON (*.json)"))
        self.inBrowse.clicked.connect(lambda: self._pick(self.inFile, "Emergent (*.em);;All files (*.*)"))
        self.outBrowse.clicked.connect(lambda: self._save(self.outFile, "Text (*.txt);;All files (*.*)"))
        self.runBtn.clicked.connect(self._run)

    def _pick(self, edit: QtWidgets.QLineEdit, filt: str):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open", "", filt)
        if p: edit.setText(p)

    def _save(self, edit: QtWidgets.QLineEdit, filt: str):
        p, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save As", edit.text() or "roundtrip.txt", filt)
        if p: edit.setText(p)

    def _run(self):
        cb_path = self.codebookPath.text().strip()
        try:
            cb = Codebook.load(cb_path)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to load codebook: {e}"); return

        emergent = self.textIn.toPlainText().strip()
        if not emergent and self.inFile.text().strip():
            try:
                emergent = read_text_any(self.inFile.text().strip())
                self.textIn.setPlainText(emergent)
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Error", f"Failed to read input file: {e}"); return

        plain = em_decode(emergent, cb)
        self.textOut.setPlainText(plain)

        if self.outFile.text().strip():
            try:
                Path(self.outFile.text().strip()).write_text(plain, encoding="utf-8")
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Error", f"Failed to save output: {e}")


# ----------------------------- Demo Tab -----------------------------
@dataclass
class DemoConfig:
    a_text: str = "params? v.new test"
    b_text: str = "ckpt v0.44 opt=adam"
    structure: float = 0.2
    seed: int = 42
    after_delay_ms: int = 2200
    type_speed_ms: int = 15


class Typewriter(QtCore.QObject):
    finished = QtCore.Signal()
    def __init__(self, target: QtWidgets.QPlainTextEdit, text: str, interval_ms: int = 15, parent=None):
        super().__init__(parent)
        self._target = target; self._text = text; self._i = 0
        self._timer = QtCore.QTimer(self); self._timer.timeout.connect(self._tick); self._timer.setInterval(interval_ms)
    def start(self):
        self._target.clear(); self._i = 0; self._timer.start()
    def _tick(self):
        if self._i >= len(self._text):
            self._timer.stop(); self.finished.emit(); return
        self._target.moveCursor(QtGui.QTextCursor.End)
        self._target.insertPlainText(self._text[self._i]); self._i += 1


class DemoTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cfg = DemoConfig(); self._build_ui(); self._wire()

    def _build_ui(self):
        self.codebookEdit = QtWidgets.QLineEdit("codebook.json")
        self.codebookBtn = QtWidgets.QPushButton("Browse…")
        self.structSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal); self.structSlider.setRange(0, 100); self.structSlider.setValue(int(self.cfg.structure * 100))
        self.structLabel = QtWidgets.QLabel(f"Structure: {self.cfg.structure:.2f}")
        self.seedSpin = QtWidgets.QSpinBox(); self.seedSpin.setRange(0, 2**31-1); self.seedSpin.setValue(self.cfg.seed)
        self.runBtn = QtWidgets.QPushButton("Run demo"); self.runBtn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
        self.runBtn.setStyleSheet(
            "QPushButton { background-color: #16a34a; color: white; font-weight: 600; padding: 6px 12px; border-radius: 6px; }"
            "QPushButton:disabled { background-color: #9ca3af; color: white; }"
            "QPushButton:hover:!disabled { background-color: #15803d; }"
        )

        self.aEdit = QtWidgets.QLineEdit(self.cfg.a_text)
        self.bEdit = QtWidgets.QLineEdit(self.cfg.b_text)

        self.A_enc = QtWidgets.QPlainTextEdit(); self._prep(self.A_enc, "A (encoded)")
        self.B_enc = QtWidgets.QPlainTextEdit(); self._prep(self.B_enc, "B (encoded)")
        self.A_dec = QtWidgets.QPlainTextEdit(); self._prep(self.A_dec, "A decoded")
        self.B_dec = QtWidgets.QPlainTextEdit(); self._prep(self.B_dec, "B decoded")

        toolbar = QtWidgets.QGridLayout()
        toolbar.addWidget(QtWidgets.QLabel("Codebook"), 0, 0); toolbar.addWidget(self.codebookEdit, 0, 1); toolbar.addWidget(self.codebookBtn, 0, 2)
        toolbar.addWidget(QtWidgets.QLabel("Structure"), 1, 0); toolbar.addWidget(self.structSlider, 1, 1); toolbar.addWidget(self.structLabel, 1, 2)
        toolbar.addWidget(QtWidgets.QLabel("Seed"), 2, 0); toolbar.addWidget(self.seedSpin, 2, 1); toolbar.addWidget(self.runBtn, 2, 2)

        demoRow = QtWidgets.QHBoxLayout()
        demoRow.addWidget(QtWidgets.QLabel("A text:")); demoRow.addWidget(self.aEdit)
        demoRow.addSpacing(12); demoRow.addWidget(QtWidgets.QLabel("B text:")); demoRow.addWidget(self.bEdit); demoRow.addStretch(1)

        grid = QtWidgets.QGridLayout()
        grid.addWidget(self.A_enc, 0, 0); grid.addWidget(self.B_enc, 0, 1)
        grid.addWidget(self.A_dec, 1, 0); grid.addWidget(self.B_dec, 1, 1)
        grid.setRowStretch(0, 1); grid.setRowStretch(1, 1)
        grid.setColumnStretch(0, 1); grid.setColumnStretch(1, 1)

        v = QtWidgets.QVBoxLayout(self)
        v.addLayout(toolbar); v.addSpacing(6); v.addLayout(demoRow); v.addSpacing(6); v.addLayout(grid)
        self.status = QtWidgets.QLabel(""); v.addWidget(self.status)

    def _prep(self, box: QtWidgets.QPlainTextEdit, ph: str):
        box.setReadOnly(True); box.setPlaceholderText(ph)
        f = box.font(); f.setFamily("DejaVu Sans"); box.setFont(f)

    def _wire(self):
        self.codebookBtn.clicked.connect(self._pick_cb)
        self.structSlider.valueChanged.connect(lambda v: self.structLabel.setText(f"Structure: {v/100:.2f}"))
        self.runBtn.clicked.connect(self._run)

    def _pick_cb(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose codebook", self.codebookEdit.text(), "JSON (*.json)")
        if p: self.codebookEdit.setText(p)

    def _load_cb(self) -> Optional[Codebook]:
        try:
            return Codebook.load(self.codebookEdit.text().strip())
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to load codebook: {e}")
            return None

    def _run(self):
        self.A_enc.clear(); self.B_enc.clear(); self.A_dec.clear(); self.B_dec.clear()
        cb = self._load_cb()
        if not cb: return

        a_text = self.aEdit.text(); b_text = self.bEdit.text()
        structure = self.structSlider.value()/100.0; seed = self.seedSpin.value()

        try:
            a_em = em_encode(a_text, cb, structure=structure, seed=seed)
            b_em = em_encode(b_text, cb, structure=structure, seed=seed)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Encode error: {e}"); return

        self._tw_a = Typewriter(self.A_enc, a_em, interval_ms=15)
        self._tw_b = Typewriter(self.B_enc, b_em, interval_ms=15)
        self._done = 0
        def _one():
            self._done += 1
            if self._done == 2:
                QtCore.QTimer.singleShot(2200, lambda: self._show_decoded(a_em, b_em, cb))
        self._tw_a.finished.connect(_one); self._tw_b.finished.connect(_one)
        self._tw_a.start(); self._tw_b.start()

    def _show_decoded(self, a_em: str, b_em: str, cb: Codebook):
        a_plain = em_decode(a_em, cb); b_plain = em_decode(b_em, cb)
        self.A_dec.setPlainText(a_plain); self.B_dec.setPlainText(b_plain)


# ----------------------------- Main Window -----------------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EmerLang GUI")
        self.resize(800, 600)

        # Try to load packaged icon from src/emerlang/assets/app.png; ignore if missing
        try:
            from importlib import resources
            res = resources.files("emerlang").joinpath("assets/app.png")
            if res and res.is_file():
                with resources.as_file(res) as p:
                    self.setWindowIcon(QtGui.QIcon(str(p)))
        except Exception:
            pass  # fall back to default Qt icon

        tabs = QtWidgets.QTabWidget()
        self.buildTab = BuildTab()
        self.encodeTab = EncodeTab()
        self.decodeTab = DecodeTab()
        self.demoTab = DemoTab()

        tabs.addTab(self.buildTab, "Build")
        tabs.addTab(self.encodeTab, "Encode")
        tabs.addTab(self.decodeTab, "Decode")
        tabs.addTab(self.demoTab, "Demo")

        self.buildTab.built.connect(self._on_built)

        self.setCentralWidget(tabs)

    def _on_built(self, cb_path: str):
        self.encodeTab.codebookPath.setText(cb_path)
        self.decodeTab.codebookPath.setText(cb_path)
        self.demoTab.codebookEdit.setText(cb_path)


def main():
    app = QtWidgets.QApplication([])
    w = MainWindow()
    w.show()
    app.exec()


if __name__ == "__main__":
    main()


# === Advanced toggles (Dialect / Space-stego / XOR) integrated into existing GUI ===
try:
    from emerlang.encoder import encode_with_dialect as _encode_with_dialect
except Exception:
    _encode_with_dialect = None

from emerlang.stego.spacesteg import encode as _space_encode, decode as _space_decode
from emerlang.crypto import xor_stream as _xor_stream

ADVANCED_DOCK = None
_ORIG_EM_ENCODE = em_encode
_ORIG_EM_DECODE = em_decode

class _AdvancedDock(QtWidgets.QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Advanced", parent)
        w = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(w)

        # Dialect
        self.chkDialect = QtWidgets.QCheckBox("Use dialect remap")
        self.dialectSeed = QtWidgets.QSpinBox(); self.dialectSeed.setRange(0, 2**31-1); self.dialectSeed.setValue(99)
        row = QtWidgets.QHBoxLayout(); row.addWidget(self.chkDialect); row.addWidget(QtWidgets.QLabel("seed")); row.addWidget(self.dialectSeed)
        form.addRow(row)

        # Space-stego
        self.chkSpace = QtWidgets.QCheckBox("Space-stego (invisible trailer)")
        self.spaceBytes = QtWidgets.QSpinBox(); self.spaceBytes.setRange(0, 100000); self.spaceBytes.setValue(0)
        form.addRow(self.chkSpace)
        form.addRow(QtWidgets.QLabel("Decode bytes (optional):"))
        form.addRow(self.spaceBytes)

        # XOR (toy)
        self.chkXor = QtWidgets.QCheckBox("Toy XOR (NOT secure)")
        self.xorKey = QtWidgets.QLineEdit(); self.xorKey.setPlaceholderText("key")
        self.xorNonce = QtWidgets.QLineEdit(); self.xorNonce.setPlaceholderText("nonce (optional)")
        row2 = QtWidgets.QHBoxLayout(); row2.addWidget(self.chkXor); row2.addWidget(self.xorKey); row2.addWidget(self.xorNonce)
        form.addRow(row2)

        self.setWidget(w)

def _install_advanced(main_window: QtWidgets.QMainWindow):
    global ADVANCED_DOCK, em_encode, em_decode, _ORIG_EM_ENCODE, _ORIG_EM_DECODE
    if ADVANCED_DOCK is not None:
        return
    ADVANCED_DOCK = _AdvancedDock(main_window)
    try:
        main_window.addDockWidget(QtCore.Qt.BottomDockWidgetArea, ADVANCED_DOCK)
    except Exception:
        # If not a QMainWindow for some reason, just show as standalone
        ADVANCED_DOCK.show()

    # Monkeypatch encode/decode used by GUI
    def _encode_wrapper(text: str, codebook, structure: float = 0.2, seed: int = 42) -> str:
        # core
        emergent = _ORIG_EM_ENCODE(text, codebook, structure=structure, seed=seed)
        # dialect
        if _encode_with_dialect and ADVANCED_DOCK.chkDialect.isChecked():
            emergent = _encode_with_dialect(text, codebook, structure=structure, seed=seed,
                                            dialect_seed=int(ADVANCED_DOCK.dialectSeed.value()))
        # space-stego
        if ADVANCED_DOCK.chkSpace.isChecked():
            emergent = _space_encode("", emergent.encode("utf-8")).decode("utf-8", "replace") if False else \
                       _space_encode("", emergent.encode("utf-8"))  # returns str
        # XOR
        if ADVANCED_DOCK.chkXor.isChecked() and ADVANCED_DOCK.xorKey.text():
            b = _xor_stream(emergent.encode("utf-8"),
                            ADVANCED_DOCK.xorKey.text().encode("utf-8"),
                            ADVANCED_DOCK.xorNonce.text().encode("utf-8"))
            emergent = b.decode("utf-8", "replace")
        return emergent

    def _decode_wrapper(emergent: str, codebook) -> str:
        src = emergent
        # XOR first (if applied during encode)
        if ADVANCED_DOCK.chkXor.isChecked() and ADVANCED_DOCK.xorKey.text():
            b = _xor_stream(src.encode("utf-8", "replace"),
                            ADVANCED_DOCK.xorKey.text().encode("utf-8"),
                            ADVANCED_DOCK.xorNonce.text().encode("utf-8"))
            src = b.decode("utf-8", "replace")
        # space-stego (if used)
        if ADVANCED_DOCK.chkSpace.isChecked():
            bits = int(ADVANCED_DOCK.spaceBytes.value()) * 8 if ADVANCED_DOCK.spaceBytes.value() else len(src) * 8
            payload = _space_decode(src, bits)
            try:
                src = payload.decode("utf-8", "replace")
            except Exception:
                pass
        return _ORIG_EM_DECODE(src, codebook)

    # Replace module-level references
    em_encode = _encode_wrapper
    em_decode = _decode_wrapper

# Hook into MainWindow creation: install dock after MainWindow is shown
_old_MainWindow_init = MainWindow.__init__
def _mw_init(self, *a, **kw):
    _old_MainWindow_init(self, *a, **kw)
    try:
        _install_advanced(self)
    except Exception as e:
        # non-fatal
        pass
MainWindow.__init__ = _mw_init
