from __future__ import annotations
from pathlib import Path
from typing import Optional
from PySide6 import QtCore, QtWidgets

from emerlang import Codebook
from emerlang.encoder import encode_with_dialect as em_encode_dialect
from emerlang.decoder import decode as em_decode
from emerlang.stego.jsonsteg import encode_json as json_encode, decode_json as json_decode
from emerlang.stego.spacesteg import encode as space_encode, decode as space_decode
from emerlang.crypto import xor_stream

class PlusWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EmerLang GUI Plus")
        self.resize(960, 680)
        self._build()

    def _build(self):
        grid = QtWidgets.QGridLayout()

        self.codebookPath = QtWidgets.QLineEdit()
        self.codebookBrowse = QtWidgets.QPushButton("Browse codebook.json")
        grid.addWidget(QtWidgets.QLabel("Codebook:"), 0, 0)
        grid.addWidget(self.codebookPath, 0, 1)
        grid.addWidget(self.codebookBrowse, 0, 2)

        self.inputText = QtWidgets.QPlainTextEdit()
        self.outputText = QtWidgets.QPlainTextEdit()
        grid.addWidget(QtWidgets.QLabel("Input:"), 1, 0)
        grid.addWidget(self.inputText, 1, 1, 1, 2)
        grid.addWidget(QtWidgets.QLabel("Output:"), 2, 0)
        grid.addWidget(self.outputText, 2, 1, 1, 2)

        # Options
        opts = QtWidgets.QGroupBox("Options")
        form = QtWidgets.QFormLayout(opts)

        self.chkDialect = QtWidgets.QCheckBox("Use dialect remap")
        self.dialectSeed = QtWidgets.QSpinBox(); self.dialectSeed.setRange(0, 2**31-1); self.dialectSeed.setValue(99)
        row = QtWidgets.QHBoxLayout(); row.addWidget(self.chkDialect); row.addWidget(QtWidgets.QLabel("seed")); row.addWidget(self.dialectSeed)
        form.addRow(row)

        self.chkXor = QtWidgets.QCheckBox("Toy XOR (NOT secure)")
        self.xorKey = QtWidgets.QLineEdit(); self.xorKey.setPlaceholderText("key")
        self.xorNonce = QtWidgets.QLineEdit(); self.xorNonce.setPlaceholderText("nonce (optional)")
        row2 = QtWidgets.QHBoxLayout(); row2.addWidget(self.chkXor); row2.addWidget(self.xorKey); row2.addWidget(self.xorNonce)
        form.addRow(row2)

        self.chkSpaceSteg = QtWidgets.QCheckBox("Embed in text (space-stego)")
        self.spaceCarrier = QtWidgets.QPlainTextEdit()
        self.spaceBytes = QtWidgets.QSpinBox(); self.spaceBytes.setRange(0, 10_000); self.spaceBytes.setValue(0)
        form.addRow(self.chkSpaceSteg)
        form.addRow(QtWidgets.QLabel("Carrier text (for space-stego):"))
        form.addRow(self.spaceCarrier)

        self.chkJsonSteg = QtWidgets.QCheckBox("Embed in JSON")
        self.jsonCarrier = QtWidgets.QPlainTextEdit()
        self.jsonNumKeys = QtWidgets.QLineEdit(); self.jsonNumKeys.setPlaceholderText("numeric keys: a,b,c")
        self.jsonStrKeys = QtWidgets.QLineEdit(); self.jsonStrKeys.setPlaceholderText("string keys: name,title")
        form.addRow(self.chkJsonSteg)
        form.addRow(self.jsonNumKeys)
        form.addRow(self.jsonStrKeys)
        form.addRow(QtWidgets.QLabel("Carrier JSON:"))
        form.addRow(self.jsonCarrier)

        # Buttons
        self.btnEncode = QtWidgets.QPushButton("Encode ▶")
        self.btnDecode = QtWidgets.QPushButton("Decode ◀")
        rowb = QtWidgets.QHBoxLayout(); rowb.addWidget(self.btnEncode); rowb.addWidget(self.btnDecode)

        v = QtWidgets.QVBoxLayout(self)
        v.addLayout(grid)
        v.addWidget(opts)
        v.addLayout(rowb)

        # wiring
        self.codebookBrowse.clicked.connect(self._browse_codebook)
        self.btnEncode.clicked.connect(self._do_encode)
        self.btnDecode.clicked.connect(self._do_decode)

    def _browse_codebook(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select codebook.json", "", "JSON (*.json)")
        if path:
            self.codebookPath.setText(path)

    def _load_cb(self) -> Codebook:
        p = self.codebookPath.text().strip()
        if not p:
            raise RuntimeError("Set codebook.json path")
        return Codebook.load(p)

    def _apply_xor(self, data: bytes) -> bytes:
        if self.chkXor.isChecked() and self.xorKey.text():
            return xor_stream(data, self.xorKey.text().encode("utf-8"), self.xorNonce.text().encode("utf-8"))
        return data

    def _do_encode(self):
        cb = self._load_cb()
        txt = self.inputText.toPlainText()

        # core encode with optional dialect
        if self.chkDialect.isChecked():
            emergent = em_encode_dialect(txt, cb, dialect_seed=int(self.dialectSeed.value()))
        else:
            emergent = em_encode_dialect(txt, cb, dialect_seed=None)

        # JSON stego route
        if self.chkJsonSteg.isChecked():
            try:
                carrier = self.jsonCarrier.toPlainText()
                num_keys = [k for k in self.jsonNumKeys.text().split(",") if k.strip()]
                str_keys = [k for k in self.jsonStrKeys.text().split(",") if k.strip()]
                out = json_encode(carrier, emergent.encode("utf-8"), channel="order+zwsp+numeric",
                                  numeric_keys=num_keys, string_keys=str_keys)
                self.outputText.setPlainText(out)
                return
            except Exception as e:
                self.outputText.setPlainText(f"[json-stego error] {e}")
                return

        # Space stego route
        if self.chkSpaceSteg.isChecked():
            carrier = self.spaceCarrier.toPlainText()
            out = space_encode(carrier, emergent.encode("utf-8"))
            self.outputText.setPlainText(out)
            return

        # XOR route (bytes -> show as replacement decoded)
        if self.chkXor.isChecked() and self.xorKey.text():
            b = self._apply_xor(emergent.encode("utf-8"))
            self.outputText.setPlainText(b.decode("utf-8", errors="replace"))
            return

        # default: just emergent text
        self.outputText.setPlainText(emergent)

    def _do_decode(self):
        cb = self._load_cb()
        src = self.inputText.toPlainText()

        # JSON stego path
        if self.chkJsonSteg.isChecked():
            try:
                payload = json_decode(src)
                text = payload.decode("utf-8", errors="replace")
                plain = em_decode(text, cb)
                self.outputText.setPlainText(plain)
                return
            except Exception as e:
                self.outputText.setPlainText(f"[json-stego decode error] {e}")
                return

        # Space stego path
        if self.chkSpaceSteg.isChecked():
            bits = int(self.spaceBytes.value()) * 8 if self.spaceBytes.value() else len(src) * 8
            payload = space_decode(src, bits)
            text = payload.decode("utf-8", errors="replace")
            plain = em_decode(text, cb)
            self.outputText.setPlainText(plain)
            return

        # XOR path
        if self.chkXor.isChecked() and self.xorKey.text():
            b = src.encode("utf-8", "replace")
            b = self._apply_xor(b)
            src = b.decode("utf-8", errors="replace")

        # default
        plain = em_decode(src, cb)
        self.outputText.setPlainText(plain)

def main():
    app = QtWidgets.QApplication([])
    w = PlusWindow()
    w.show()
    app.exec()

if __name__ == "__main__":
    main()
