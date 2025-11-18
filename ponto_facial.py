# 👨🏻‍💻 Código completo do sistema de registro/marcação de ponto

"""
Sistema simples de marcação de ponto por detecção facial (desktop).
- GUI: Tkinter
- Camera: OpenCV
- Reconhecimento facial: face_recognition (dlib)
- Banco local: SQLite (arquivo attendance.db)
- Encodings faciais: salvos em ./faces/<matricula>.pkl

Fluxo:
- Cadastrar usuário: captura foto, extrai encoding, salva
- Marcar ponto: seleciona ação, tira foto, compara com encodings e grava registro com timestamp
"""

import os
import cv2
import time
import pickle
import sqlite3
import threading
import numpy as np
from datetime import datetime
from tkinter import Tk, Label, Button, Entry, StringVar, OptionMenu, messagebox, Frame
from PIL import Image, ImageTk
import face_recognition

# --- Configurações ---
FACES_DIR = "faces"
DB_FILE = "attendance.db"
MATCH_THRESHOLD = 0.5  # menor -> mais rígido. 0.4-0.6 é faixa comum.

ACTIONS = [
    "Início do expediente",
    "Saída para almoço",
    "Volta do almoço",
    "Fim do expediente"
]

# --- Inicialização de pastas / DB ---
os.makedirs(FACES_DIR, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matricula TEXT UNIQUE,
            nome TEXT,
            face_path TEXT,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matricula TEXT,
            nome TEXT,
            action TEXT,
            timestamp TEXT,
            confidence REAL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- Utilitários de face / storage ---
def save_face_encoding(matricula: str, nome: str, image_bgr):
    """
    Extrai encoding da imagem BGR e salva em arquivo (pickle).
    Também grava o registro do funcionário no SQLite.
    """
    rgb = image_bgr[:, :, ::-1]  # BGR -> RGB
    faces = face_recognition.face_locations(rgb)
    if len(faces) == 0:
        raise ValueError("Nenhum rosto detectado. Posicione-se melhor e tente novamente.")
    # pega o primeiro rosto
    encoding = face_recognition.face_encodings(rgb, known_face_locations=faces)[0]
    file_path = os.path.join(FACES_DIR, f"{matricula}.pkl")
    with open(file_path, "wb") as f:
        pickle.dump({
            "matricula": matricula,
            "nome": nome,
            "encoding": encoding
        }, f)
    # salvar metadados no SQLite (ou atualizar se já existir)
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute("""
        INSERT OR REPLACE INTO employees (matricula, nome, face_path, created_at)
        VALUES (?, ?, ?, ?)
    """, (matricula, nome, file_path, now))
    conn.commit()
    conn.close()
    return file_path

def load_all_known_encodings():
    """Carrega todos os encodings de ./faces/*.pkl"""
    encodings = []
    metadata = []
    for fname in os.listdir(FACES_DIR):
        if not fname.endswith(".pkl"):
            continue
        path = os.path.join(FACES_DIR, fname)
        try:
            with open(path, "rb") as f:
                obj = pickle.load(f)
            encodings.append(obj["encoding"])
            metadata.append({
                "matricula": obj["matricula"],
                "nome": obj["nome"],
                "path": path
            })
        except Exception as e:
            print("Falha ao carregar encoding", path, e)
    return np.array(encodings), metadata

def register_attendance(matricula, nome, action, confidence):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    ts = datetime.now().isoformat(sep=' ', timespec='seconds')
    cur.execute("""
        INSERT INTO attendance (matricula, nome, action, timestamp, confidence)
        VALUES (?, ?, ?, ?, ?)
    """, (matricula, nome, action, ts, float(confidence)))
    conn.commit()
    conn.close()

# --- GUI + Captura de camera ---
class App:
    def __init__(self, window):
        self.window = window
        self.window.title("Marcação de Ponto - Reconhecimento Facial")
        self.window.geometry("900x600")
        self.video_capture = cv2.VideoCapture(0)
        self.current_frame = None
        self.running = True

        # UI: preview da camera
        self.preview_label = Label(window)
        self.preview_label.pack()

        # Controls frame
        controls = Frame(window)
        controls.pack(pady=10)

        # Registration inputs
        Label(controls, text="Nome:").grid(row=0, column=0)
        self.name_var = StringVar()
        Entry(controls, textvariable=self.name_var, width=20).grid(row=0, column=1)

        Label(controls, text="Matrícula:").grid(row=0, column=2)
        self.matricula_var = StringVar()
        Entry(controls, textvariable=self.matricula_var, width=12).grid(row=0, column=3)

        Button(controls, text="Cadastrar Usuário (foto)", command=self.threaded_register).grid(row=0, column=4, padx=8)

        # Attendance selection
        Label(controls, text="Ação:").grid(row=1, column=0, pady=8)
        self.action_var = StringVar()
        self.action_var.set(ACTIONS[0])
        OptionMenu(controls, self.action_var, *ACTIONS).grid(row=1, column=1)

        Button(controls, text="Marcar Ponto (foto)", command=self.threaded_mark).grid(row=1, column=4, padx=8)

        # Utility buttons
        Button(controls, text="Exportar registros CSV", command=self.export_csv).grid(row=2, column=0, pady=10)
        Button(controls, text="Limpar logs (cuidado)", command=self.clear_logs).grid(row=2, column=1, pady=10)

        # Status label
        self.status_label = Label(window, text="Status: pronto", fg="green")
        self.status_label.pack(pady=6)

        # Carregar encodings conhecidos
        self.known_encodings, self.known_meta = load_all_known_encodings()

        # Start video loop
        self.update_video()

        # on close
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def update_video(self):
        if not self.running:
            return
        ret, frame = self.video_capture.read()
        if not ret:
            self.status_label.config(text="Erro ao acessar câmera", fg="red")
            return
        # reduz tamanho para melhorar performance (opcional)
        small = cv2.resize(frame, (0, 0), fx=0.6, fy=0.6)
        self.current_frame = small
        # converte BGR -> RGB para exibir
        img = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img)
        imgtk = ImageTk.PhotoImage(image=img_pil)
        self.preview_label.imgtk = imgtk
        self.preview_label.configure(image=imgtk)
        # repete em ~30 ms
        self.window.after(30, self.update_video)

    # --- threading helpers para não travar a GUI ---
    def threaded_register(self):
        t = threading.Thread(target=self.register_user)
        t.start()

    def threaded_mark(self):
        t = threading.Thread(target=self.mark_point)
        t.start()

    # --- operações principais ---
    def register_user(self):
        nome = self.name_var.get().strip()
        matricula = self.matricula_var.get().strip()
        if not nome or not matricula:
            messagebox.showwarning("Dados faltando", "Informe nome e matrícula antes de cadastrar.")
            return
        frame = self.current_frame
        if frame is None:
            messagebox.showerror("Câmera", "Quadro da câmera indisponível.")
            return
        try:
            self.status_label.config(text="Detectando rosto e salvando...", fg="blue")
            face_path = save_face_encoding(matricula, nome, frame)
            # recarrega encodings
            self.known_encodings, self.known_meta = load_all_known_encodings()
            self.status_label.config(text=f"Usuário {nome} cadastrado com sucesso.", fg="green")
            messagebox.showinfo("Sucesso", f"Usuário {nome} ({matricula}) cadastrado.")
        except Exception as e:
            self.status_label.config(text="Falha no cadastro", fg="red")
            messagebox.showerror("Erro ao cadastrar", str(e))

    def mark_point(self):
        action = self.action_var.get()
        frame = self.current_frame
        if frame is None:
            messagebox.showerror("Câmera", "Quadro da câmera indisponível.")
            return
        if self.known_encodings.size == 0:
            messagebox.showwarning("Sem usuários cadastrados", "Nenhum usuário cadastrado no sistema.")
            return
        self.status_label.config(text="Detectando rosto e comparando...", fg="blue")
        rgb = frame[:, :, ::-1]
        face_locations = face_recognition.face_locations(rgb)
        if len(face_locations) == 0:
            self.status_label.config(text="Nenhum rosto detectado.", fg="red")
            messagebox.showwarning("Sem rosto", "Nenhum rosto detectado. Posicione-se corretamente e tente de novo.")
            return
        encoding = face_recognition.face_encodings(rgb, known_face_locations=face_locations)[0]
        # compara com todos conhecidos
        distances = face_recognition.face_distance(self.known_encodings, encoding)
        best_idx = np.argmin(distances)
        best_distance = float(distances[best_idx])
        confidence = 1.0 - best_distance  # métrica simples: quanto menor a distância, maior a confiança
        if best_distance <= MATCH_THRESHOLD:
            matched = self.known_meta[best_idx]
            matricula = matched["matricula"]
            nome = matched["nome"]
            register_attendance(matricula, nome, action, confidence)
            self.status_label.config(text=f"Ponto registrado: {nome} - {action}", fg="green")
            messagebox.showinfo("Ponto registrado", f"{nome} ({matricula})\nAção: {action}\nConfiança: {confidence:.3f}")
        else:
            self.status_label.config(text="Rosto não reconhecido (falha).", fg="red")
            messagebox.showerror("Não reconhecido", f"Rosto não reconhecido. Distância mínima: {best_distance:.3f}")

    # --- utilitários ---
    def export_csv(self):
        import csv
        out = "attendance_export.csv"
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT matricula, nome, action, timestamp, confidence FROM attendance ORDER BY timestamp DESC")
        rows = cur.fetchall()
        conn.close()
        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["matricula", "nome", "action", "timestamp", "confidence"])
            writer.writerows(rows)
        messagebox.showinfo("Exportado", f"Registros exportados para {out}")

    def clear_logs(self):
        if not messagebox.askyesno("Confirmar", "Deseja realmente apagar todos os registros de ponto?"):
            return
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("DELETE FROM attendance")
        conn.commit()
        conn.close()
        messagebox.showinfo("Pronto", "Registros apagados.")

    def on_close(self):
        self.running = False
        try:
            self.video_capture.release()
        except:
            pass
        self.window.destroy()

if __name__ == "__main__":
    root = Tk()
    app = App(root)
    root.mainloop()
