# 🕒 Sistema de Marcação de Ponto por Reconhecimento Facial


Este projeto implementa um **sistema completo de marcação de ponto** utilizando **reconhecimento facial**, permitindo que colaboradores registrem:

- Início do expediente  
- Saída para o almoço  
- Volta do almoço  
- Fim do expediente  

O sistema foi projetado para ser rápido, seguro e de fácil uso, utilizando webcam para capturar o rosto e validar o colaborador automaticamente.

---

# 🖼️ Visão Geral do Sistema

## 📸 Tela Principal – Câmera em Tempo Real

A interface principal exibe:

- Preview da câmera  
- Botões de cadastro  
- Botões de marcação de ponto  
- Seleção da ação (início, almoço, retorno, fim)  
- Mensagens de status  

---

## 👤 Cadastro de Usuário – Captura Facial
Ao cadastrar um usuário:

1. A câmera captura uma imagem do rosto.
2. O sistema extrai o *face encoding*.
3. Salva os dados em `faces/<matricula>.pkl`.
4. Registra no banco SQLite.

---

## 🕝 Marcação de Ponto – Reconhecimento Facial

O colaborador seleciona a ação desejada e tira a foto.

O sistema:

- Detecta o rosto  
- Compara o encoding com o banco  
- Registra a ação no banco  
- Mostra o nível de confiança  

---

## 📊 Exportação de Registros

Com um clique, todos os registros são exportados para um arquivo CSV.

---

# 📂 Estrutura do Projeto
/
├── ponto_facial.py
├── attendance.db
├── faces/
│ ├── 12345.pkl
│ ├── 94821.pkl
│ └── ...
├── attendance_export.csv (opcional)
└── README.md
---

# 🚀 Instalação

## 1️⃣ Criar ambiente virtual
```bash
python -m venv venv
venv\Scripts\activate
2️⃣ Instalar dependências
pip install opencv-python face_recognition Pillow numpy pyodbc

▶️ Executando o Sistema
python ponto_facial.py

🔍 Funcionamento do Reconhecimento Facial

O sistema realiza:

Detecção do rosto

Extração do encoding

Cálculo da distância facial

Confirmação da identidade

Registro da ação no banco

🔐 Segurança e LGPD

Este sistema utiliza dados biométricos (rostos).
Recomenda-se:

Restrição de acesso ao diretório faces/

Criptografia dos encodings

Backup periódico

Consentimento dos colaboradores

🗺️ Roadmap

 Integração com MS SQL Server

 Liveness Detection (anti-fraude)

 Dashboard avançado

 App mobile

 Versão Web

🤝 Contribuindo

Pull requests são bem-vindos!
Para grandes mudanças, abra uma issue antes.

📬 Contato

Precisa de:

documentação profissional,

telas personalizadas,

versão empresarial,

ou integração completa com IA?

É só me chamar!

📄 Licença

Este projeto pode ser usado livremente para fins educacionais ou corporativos internos.
