# UNIMAR - Sistema de Cuestionarios y Evaluaciones

Este repositorio contiene el prototipo funcional de la Plataforma de Evaluaciones para la **Universidad de Margarita (UNIMAR)**. El sistema está desarrollado con un backend en **Flask** y **SQLite**, complementado con una interfaz de usuario dinámica y moderna de alto contraste optimizada mediante **Tailwind CSS**.

El proyecto incluye control de roles (Profesores y Estudiantes) y persistencia de datos segura (idempotente).

---

**Instrucciones de INICIO**
1. Inicializar la Base de Datos
    ```python seed.py```
2. Iniciar el Servidor Web
   ```python app.py```
3. Acceso en el Navegador
   [http://127.0.0.1:5000](http://127.0.0.1:5000)

**Credenciales de Acceso**
Correo Electrónico	Contraseña
profesor@demo.com	prof123
estudiante@demo.com	est123

## Requisitos Previos

Antes de ejecutar la aplicación, asegúrese de tener instalado Python en su sistema. Se recomienda instalar las dependencias necesarias ejecutando el siguiente comando en la terminal:

```bash
    pip install flask werkzeug
