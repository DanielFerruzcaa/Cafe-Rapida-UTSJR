import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename

# Configuración de Flask
app = Flask(__name__)
app.secret_key = 'clave_secreta_predeterminada'

# Carpeta para subir imágenes
UPLOAD_FOLDER = os.path.join('static', 'img')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Validar extensión de archivo
def extension_valida(nombre):
    return '.' in nombre and nombre.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Conexión SQLite
def get_db_connection():
    conexion = sqlite3.connect("cafe_rapida.db")
    conexion.row_factory = sqlite3.Row
    return conexion

# Página principal
@app.route('/')
def index():
    return render_template('index.html')

# Login (igual que antes)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']
        
        # Si es el admin
        if usuario == 'cafeteria':
            if password == '1234':  # Contraseña del admin
                session['usuario'] = usuario
                return redirect(url_for('panel'))
            else:
                return render_template('login.html', error="Contraseña incorrecta")

        # Si es comprador
        else:
            session['usuario'] = usuario
            return redirect(url_for('menu'))

    return render_template('login.html')


# Menú comprador
@app.route('/menu')
def menu():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    conexion = get_db_connection()
    productos = conexion.execute("SELECT * FROM productos ORDER BY categoria").fetchall()
    conexion.close()
    return render_template('menu.html', productos=productos, usuario=session['usuario'])

# Cerrar sesión
@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('index'))

# Panel vendedor
@app.route('/panel')
def panel():
    if 'usuario' not in session or session['usuario'] != 'cafeteria':
        return redirect(url_for('login'))

    conexion = get_db_connection()
    productos = conexion.execute("SELECT * FROM productos ORDER BY categoria").fetchall()
    conexion.close()
    return render_template('panel.html', productos=productos)

# Agregar producto
@app.route('/agregar', methods=['GET', 'POST'])
def agregar():
    if 'usuario' not in session or session['usuario'] != 'cafeteria':
        return redirect(url_for('login'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        unidades = request.form['unidades']
        categoria = request.form['categoria']

        imagen = request.files['imagen']
        if imagen and extension_valida(imagen.filename):
            filename = secure_filename(imagen.filename)
            ruta = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            imagen.save(ruta)
            ruta_final = f'img/{filename}'
        else:
            ruta_final = 'img/default.jpg'

        conexion = get_db_connection()
        conexion.execute(
            "INSERT INTO productos (nombre, descripcion, precio, unidades, categoria, imagen) VALUES (?, ?, ?, ?, ?, ?)",
            (nombre, descripcion, precio, unidades, categoria, ruta_final)
        )
        conexion.commit()
        conexion.close()
        return redirect(url_for('panel'))

    return render_template('agregar.html')

# Editar producto
@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    if 'usuario' not in session or session['usuario'] != 'cafeteria':
        return redirect(url_for('login'))

    conexion = get_db_connection()

    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        unidades = request.form['unidades']
        categoria = request.form['categoria']

        imagen = request.files['imagen']
        if imagen and extension_valida(imagen.filename):
            filename = secure_filename(imagen.filename)
            ruta = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            imagen.save(ruta)
            ruta_final = f'img/{filename}'
            conexion.execute(
                """UPDATE productos SET nombre=?, descripcion=?, precio=?, unidades=?, categoria=?, imagen=? WHERE id=?""",
                (nombre, descripcion, precio, unidades, categoria, ruta_final, id)
            )
        else:
            conexion.execute(
                """UPDATE productos SET nombre=?, descripcion=?, precio=?, unidades=?, categoria=? WHERE id=?""",
                (nombre, descripcion, precio, unidades, categoria, id)
            )

        conexion.commit()
        conexion.close()
        return redirect(url_for('panel'))

    producto = conexion.execute("SELECT * FROM productos WHERE id = ?", (id,)).fetchone()
    conexion.close()
    return render_template('editar.html', producto=producto)

# Eliminar producto
@app.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    if 'usuario' not in session or session['usuario'] != 'cafeteria':
        return redirect(url_for('login'))

    conexion = get_db_connection()
    conexion.execute("DELETE FROM productos WHERE id = ?", (id,))
    conexion.commit()
    conexion.close()
    return redirect(url_for('panel'))

# Carrito
def obtener_carrito():
    if 'carrito' not in session:
        session['carrito'] = []
    return session['carrito']

@app.route('/agregar_al_carrito/<int:producto_id>')
def agregar_al_carrito(producto_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    carrito = obtener_carrito()
    for item in carrito:
        if item['id'] == producto_id:
            item['cantidad'] += 1
            break
    else:
        conexion = get_db_connection()
        producto = conexion.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
        conexion.close()
        if producto:
            carrito.append({
                'id': producto['id'],
                'nombre': producto['nombre'],
                'precio': float(producto['precio']),
                'cantidad': 1,
                'imagen': producto['imagen']
            })

    session['carrito'] = carrito
    return redirect(url_for('menu'))

@app.route('/carrito')
def carrito():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    carrito = obtener_carrito()
    total = sum(item['precio'] * item['cantidad'] for item in carrito)
    return render_template('carrito.html', carrito=carrito, total=total, productos=carrito)

@app.route('/eliminar_del_carrito/<int:producto_id>')
def eliminar_del_carrito(producto_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    carrito = obtener_carrito()
    carrito = [item for item in carrito if item['id'] != producto_id]
    session['carrito'] = carrito
    return redirect(url_for('carrito'))

@app.route('/vaciar_carrito', methods=['POST'])
def vaciar_carrito():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    session['carrito'] = []
    return redirect(url_for('carrito'))

@app.route('/realizar_pedido', methods=['POST'])
def realizar_pedido():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    session.pop('carrito', None)
    return render_template('pedido_exito.html')

if __name__ == '__main__':
    app.run(debug=True)
