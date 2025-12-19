from flask import Flask, render_template_string, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, WardrobeItem, Outfit, OutfitItem, Laundry, Season, Style, OutfitSuggestion
from datetime import datetime, timezone
import random
import os

app = Flask(__name__)
app.secret_key = "virtual_wardrobe_secret"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vdrobe.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 text-gray-800">
<nav class="bg-white shadow-md">
    <div class="max-w-6xl mx-auto px-4 flex justify-between items-center py-3">
        <a href="/" class="font-bold text-indigo-600 text-lg">VirtualWardrobe</a>
        <div class="space-x-4">
            {% if session.get("user_id") %}
                <a href="/" class="text-gray-600">Builder</a>
                <a href="/wardrobe" class="text-gray-600">Wardrobe</a>
                <a href="/laundry" class="text-gray-600">Laundry</a>
                <a href="/auto" class="text-gray-600">Auto Outfit</a>
                <a href="/logout" class="text-red-600 font-semibold">Logout</a>
            {% else %}
                <a href="/login" class="text-indigo-600 font-semibold">Login</a>
                <a href="/register" class="text-indigo-600 font-semibold">Register</a>
            {% endif %}
        </div>
    </div>
</nav>
<div class="max-w-6xl mx-auto p-6">
{{ content | safe }}
</div>
</body>
</html>
"""


REGISTER_HTML = """
<div class="max-w-md mx-auto bg-white p-6 rounded-xl shadow-xl">
<h2 class="text-2xl font-bold mb-4">Register</h2>
<form method="POST">
    <input name="username" placeholder="Username" class="w-full border p-2 mb-3" required>
    <input name="email" placeholder="Email" class="w-full border p-2 mb-3" required>
    <input name="password" type="password" placeholder="Password" class="w-full border p-2 mb-3" required>
    <button class="w-full bg-indigo-600 text-white p-2 rounded-md hover:bg-indigo-700">Register</button>
</form>
<p class="mt-3">Already have an account? <a href="/login" class="text-indigo-600">Login</a></p>
</div>
"""

LOGIN_HTML = """
<div class="max-w-md mx-auto bg-white p-6 rounded-xl shadow-xl">
<h2 class="text-2xl font-bold mb-4">Login</h2>
<form method="POST">
    <input name="email" placeholder="Email" class="w-full border p-2 mb-3" required>
    <input name="password" type="password" placeholder="Password" class="w-full border p-2 mb-3" required>
    <button class="w-full bg-indigo-600 text-white p-2 rounded-md hover:bg-indigo-700">Login</button>
</form>
<p class="mt-3">Don't have an account? <a href="/register" class="text-indigo-600">Register</a></p>
</div>
"""

INDEX_HTML = """
<h1 class="text-3xl font-bold mb-6 text-center">Create Your Outfit</h1>

<div class="grid grid-cols-2 gap-6">

    <!-- LEFT SECTION: DROPZONES -->
    <div>
        <h2 class="font-semibold text-xl mb-4">Generated</h2>

        <!-- TOP DROPZONE -->
        <div id="top-dropzone" class="border-2 border-dashed p-4 text-center mb-4">
            Top
        </div>

        <!-- BOTTOM DROPZONE -->
        <div id="bottom-dropzone" class="border-2 border-dashed p-4 text-center mb-4">
            Bottom
        </div>

        <!-- SHOES DROPZONE -->
        <div id="shoes-dropzone" class="border-2 border-dashed p-4 text-center mb-4">
            Shoes
        </div>
    </div>

    <!-- RIGHT SECTION: WARDROBE -->
    <div>
        <h2 class="font-semibold text-xl mb-4">Your Wardrobe</h2>
        <div class="grid grid-cols-3 gap-3">
        {% for item in items %}
            <img src="{{ item.image_url }}"
                 class="border rounded-md cursor-pointer wardrobe-item"
                 data-category="{{ item.category }}"
                 data-image="{{ item.image_url }}">
        {% endfor %}
        </div>
    </div>

</div>

<script>
document.querySelectorAll('.wardrobe-item').forEach(item => {
    item.onclick = () => {
        let cat = item.dataset.category;
        document.getElementById(`${cat}-dropzone`).innerHTML =
            `<img src="${item.dataset.image}" class="w-full h-full object-contain">`;
    };
});
</script>

"""

WARDROBE_HTML = """
<div class="flex justify-between items-center mb-6">
    <h1 class="text-3xl font-bold">My Wardrobe</h1>
    <a href="/add" class="bg-indigo-600 text-white px-4 py-2 rounded">Add Item</a>
</div>

<div class="grid grid-cols-4 gap-4">
{% for item in items %}
<div class="bg-white p-3 rounded-lg shadow-md">
    <img src="{{ item.image_url }}" class="w-full h-40 object-cover rounded-lg">
    <p class="font-semibold">{{ item.item_name }}</p>
    <p class="text-gray-600">{{ item.category }} • {{ item.season.season_name if item.season else '' }} • {{ item.style.style_name if item.style else '' }}</p>

    <a href="/laundry/{{ item.item_id }}" class="mt-2 bg-yellow-500 text-white p-1 rounded block text-center">
        Move to Laundry
    </a>

    <form action="/delete/{{ item.item_id }}" method="POST">
        <button class="mt-2 bg-red-600 w-full text-white p-1 rounded">Delete</button>
    </form>
</div>
{% endfor %}
</div>
"""

ADD_ITEM_HTML = """
<h1 class="text-3xl font-bold mb-6 text-center">Add New Item</h1>
<form method="POST" class="max-w-md mx-auto bg-white p-6 rounded-xl shadow-xl">
    <input name="item_name" placeholder="Item Name" class="w-full border p-2 mb-3" required>
    <input name="image_url" placeholder="Image URL" class="w-full border p-2 mb-3" required>
    <select name="category" class="w-full border p-2 mb-3">
        <option value="top">Top</option>
        <option value="bottom">Bottom</option>
        <option value="shoes">Shoes</option>
    </select>

    <label class="block mb-1">Season</label>
    <select name="season_id" class="w-full border p-2 mb-3">
        {% for s in seasons %}<option value="{{ s.season_id }}">{{ s.season_name }}</option>{% endfor %}
    </select>

    <label class="block mb-1">Style</label>
    <select name="style_id" class="w-full border p-2 mb-3">
        {% for st in styles %}<option value="{{ st.style_id }}">{{ st.style_name }}</option>{% endfor %}
    </select>

    <button class="w-full bg-indigo-600 text-white p-2 rounded-md hover:bg-indigo-700">Add Item</button>
</form>
"""

LAUNDRY_HTML = """
<h2 class="text-2xl font-bold mb-4">Laundry Items</h2>
{% if items|length == 0 %}
<p>No items in laundry.</p>
{% endif %}
<div style="display:flex; gap:20px; flex-wrap:wrap;">
{% for laundry, item in items %}
    <div class="p-4 shadow-md rounded-lg border bg-white" style="width:170px;">
        <img src="{{ item.image_url }}" width="150" class="rounded mb-2">
        <p class="font-semibold">{{ item.item_name }}</p>
        <a href="/restore/{{ item.item_id }}" class="block bg-green-600 text-white text-center p-2 rounded mt-2 hover:bg-green-700">Restore</a>
    </div>
{% endfor %}
</div>
"""

AUTO_SELECT_HTML = """
<h2 class="text-2xl font-bold mb-4">Auto Outfit Generator</h2>
<form method="POST">
    <label class="block mb-2">Choose season</label>
    <select name="season_id" class="w-64 border p-2 mb-4">
        <option value="">Any</option>
        {% for s in seasons %}<option value="{{ s.season_id }}">{{ s.season_name }}</option>{% endfor %}
    </select>

    <label class="block mb-2">Choose style</label>
    <select name="style_id" class="w-64 border p-2 mb-4">
        <option value="">Any</option>
        {% for st in styles %}<option value="{{ st.style_id }}">{{ st.style_name }}</option>{% endfor %}
    </select>

    <button class="bg-indigo-600 text-white p-2 rounded">Generate Outfit</button>
</form>

{% if suggestion %}
<div class="mt-10 bg-white p-6 rounded-xl shadow max-w-xl mx-auto">

    <h3 class="font-bold text-2xl text-center mb-6">Generated Outfit</h3>

    <!-- TOP SECTION -->
    <div class="mb-6 text-center">
        <h4 class="font-semibold mb-2 text-gray-700">Top</h4>
        <img src="{{ suggestion.top.image_url }}" 
             class="w-60 h-60 object-cover rounded mx-auto shadow">
        <p class="mt-2 text-lg font-medium">{{ suggestion.top.item_name }}</p>
    </div>

    <!-- BOTTOM SECTION -->
    <div class="mb-6 text-center">
        <h4 class="font-semibold mb-2 text-gray-700">Bottom</h4>
        <img src="{{ suggestion.bottom.image_url }}" 
             class="w-60 h-60 object-cover rounded mx-auto shadow">
        <p class="mt-2 text-lg font-medium">{{ suggestion.bottom.item_name }}</p>
    </div>

    <!-- SHOES SECTION -->
    <div class="mb-6 text-center">
        <h4 class="font-semibold mb-2 text-gray-700">Shoes</h4>
        <img src="{{ suggestion.shoes.image_url }}" 
             class="w-60 h-60 object-cover rounded mx-auto shadow">
        <p class="mt-2 text-lg font-medium">{{ suggestion.shoes.item_name }}</p>
    </div>

</div>
{% endif %}

"""

# ------------------ Helper: exclude laundry ------------------
def get_available_items(user_id, season_id=None, style_id=None):
    """Return wardrobe items for the user excluding those present in Laundry."""
    q = WardrobeItem.query.filter(WardrobeItem.user_id == user_id)

    # exclude items present in laundry for this user
    subq = db.session.query(Laundry.item_id).filter_by(user_id=user_id)
    q = q.filter(~WardrobeItem.item_id.in_(subq))

    if season_id:
        q = q.filter(WardrobeItem.season_id == season_id)
    if style_id:
        q = q.filter(WardrobeItem.style_id == style_id)
    return q.all()

# ------------------ ROUTES ------------------

@app.route("/")
def index():
    if "user_id" not in session:
        return redirect("/login")

    # show last generated suggestion if exists
    last = OutfitSuggestion.query.filter_by(user_id=session["user_id"]).order_by(OutfitSuggestion.created_at.desc()).first()
    suggestion = None
    if last:
        suggestion = {
            "top": WardrobeItem.query.get(last.top_item_id) if last.top_item_id else None,
            "bottom": WardrobeItem.query.get(last.bottom_item_id) if last.bottom_item_id else None,
            "shoes": WardrobeItem.query.get(last.shoes_item_id) if last.shoes_item_id else None
        }

    items = get_available_items(session["user_id"])
    return render_template_string(BASE_TEMPLATE, title="Outfit Builder", content=render_template_string(INDEX_HTML, items=items, suggestion=suggestion))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        hash_pw = generate_password_hash(request.form["password"])
        user = User(username=request.form["username"], email=request.form["email"], password_hash=hash_pw)
        db.session.add(user)
        db.session.commit()
        return redirect("/login")
    return render_template_string(BASE_TEMPLATE, title="Register", content=REGISTER_HTML)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form["email"]).first()
        if user and check_password_hash(user.password_hash, request.form["password"]):
            session["user_id"] = user.user_id
            return redirect("/wardrobe")
    return render_template_string(BASE_TEMPLATE, title="Login", content=LOGIN_HTML)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/wardrobe")
def wardrobe():
    if "user_id" not in session:
        return redirect("/login")
    items = get_available_items(session["user_id"])
    return render_template_string(BASE_TEMPLATE, title="My Wardrobe", content=render_template_string(WARDROBE_HTML, items=items))

@app.route("/add", methods=["GET", "POST"])
def add_item():
    if "user_id" not in session:
        return redirect("/login")
    seasons = Season.query.all()
    styles = Style.query.all()

    if request.method == "POST":
        item = WardrobeItem(
            user_id=session["user_id"],
            item_name=request.form["item_name"],
            category=request.form["category"],
            image_url=request.form["image_url"],
            season_id=request.form.get("season_id") or None,
            style_id=request.form.get("style_id") or None
        )
        db.session.add(item)
        db.session.commit()
        return redirect("/wardrobe")
    return render_template_string(BASE_TEMPLATE, title="Add Item", content=render_template_string(ADD_ITEM_HTML, seasons=seasons, styles=styles))

@app.route("/delete/<int:item_id>", methods=["POST"])
def delete_item(item_id):
    item = WardrobeItem.query.get(item_id)
    if item:
        # also delete any laundry entries pointing to it
        Laundry.query.filter_by(item_id=item_id).delete()
        db.session.delete(item)
        db.session.commit()
    return redirect("/wardrobe")

@app.route("/laundry")
def laundry():
    if "user_id" not in session:
        return redirect("/login")
    items = (db.session.query(Laundry, WardrobeItem)
             .join(WardrobeItem, Laundry.item_id == WardrobeItem.item_id)
             .filter(Laundry.user_id == session["user_id"])
             .all())
    return render_template_string(BASE_TEMPLATE, title="Laundry", content=render_template_string(LAUNDRY_HTML, items=items))

@app.route("/laundry/<int:item_id>")
def move_to_laundry(item_id):
    if "user_id" not in session:
        return redirect("/login")
    # create laundry entry if not exists
    exists = Laundry.query.filter_by(item_id=item_id, user_id=session["user_id"]).first()
    if not exists:
        entry = Laundry(item_id=item_id, user_id=session["user_id"])
        db.session.add(entry)
        db.session.commit()
    return redirect("/wardrobe")

@app.route("/restore/<int:item_id>")
def restore(item_id):
    if "user_id" not in session:
        return redirect("/login")
    entry = Laundry.query.filter_by(item_id=item_id, user_id=session["user_id"]).first()
    if entry:
        db.session.delete(entry)
        db.session.commit()
    return redirect("/laundry")

@app.route("/auto", methods=["GET", "POST"])
def auto_outfit():
    if "user_id" not in session:
        return redirect("/login")
    seasons = Season.query.all()
    styles = Style.query.all()
    suggestion = None

    if request.method == "POST":
        season_id = request.form.get("season_id") or None
        style_id = request.form.get("style_id") or None

        # fetch available items by category
        tops = get_available_items(session["user_id"], season_id=season_id, style_id=style_id)
        tops = [i for i in tops if i.category == "top"]
        bottoms = get_available_items(session["user_id"], season_id=season_id, style_id=style_id)
        bottoms = [i for i in bottoms if i.category == "bottom"]
        shoes = get_available_items(session["user_id"], season_id=season_id, style_id=style_id)
        shoes = [i for i in shoes if i.category == "shoes"]

        if not tops or not bottoms or not shoes:
            # not enough items to form outfit
            suggestion = None
        else:
            top = random.choice(tops)
            bottom = random.choice(bottoms)
            shoe = random.choice(shoes)

            # save suggestion
            sug = OutfitSuggestion(
                user_id=session["user_id"],
                season_id=season_id,
                style_id=style_id,
                top_item_id=top.item_id,
                bottom_item_id=bottom.item_id,
                shoes_item_id=shoe.item_id
            )
            db.session.add(sug)
            db.session.commit()
            suggestion = {"top": top, "bottom": bottom, "shoes": shoe}

    return render_template_string(BASE_TEMPLATE, title="Auto Outfit", content=render_template_string(AUTO_SELECT_HTML, seasons=seasons, styles=styles, suggestion=suggestion))

# ------------------ DB seeding for seasons/styles ------------------
def seed_basic_data():
    # seed seasons and styles if not present
    base_seasons = ["summer", "winter", "monsoon", "all-season"]
    base_styles = ["casual", "formal", "party", "ethnic"]

    for s in base_seasons:
        if not Season.query.filter_by(season_name=s).first():
            db.session.add(Season(season_name=s))
    for st in base_styles:
        if not Style.query.filter_by(style_name=st).first():
            db.session.add(Style(style_name=st))
    db.session.commit()

if __name__ == "__main__":
    with app.app_context():
        # if you want a fresh DB: delete vdrobe.db file first, then run
        db.create_all()
        seed_basic_data()
    app.run(debug=True)
