from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    wardrobe_items = db.relationship(
        "WardrobeItem",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    outfits = db.relationship(
        "Outfit",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    outfit_suggestions = db.relationship(
        "OutfitSuggestion",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class Season(db.Model):
    __tablename__ = "seasons"
    season_id = db.Column(db.Integer, primary_key=True)
    season_name = db.Column(db.String(50), unique=True, nullable=False)

    wardrobe_items = db.relationship("WardrobeItem", back_populates="season")


class Style(db.Model):
    __tablename__ = "styles"
    style_id = db.Column(db.Integer, primary_key=True)
    style_name = db.Column(db.String(50), unique=True, nullable=False)

    wardrobe_items = db.relationship("WardrobeItem", back_populates="style")


class WardrobeItem(db.Model):
    __tablename__ = "wardrobe_items"

    item_id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(20), nullable=False)   # top, bottom, shoes
    image_url = db.Column(db.String(300), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)

    season_id = db.Column(db.Integer, db.ForeignKey("seasons.season_id"), nullable=True)
    style_id = db.Column(db.Integer, db.ForeignKey("styles.style_id"), nullable=True)

    user = db.relationship("User", back_populates="wardrobe_items")
    season = db.relationship("Season", back_populates="wardrobe_items")
    style = db.relationship("Style", back_populates="wardrobe_items")

    outfit_items = db.relationship(
        "OutfitItem",
        back_populates="item",
        cascade="all, delete-orphan"
    )


class Outfit(db.Model):
    __tablename__ = "outfits"

    outfit_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    outfit_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    is_favorite = db.Column(db.Boolean, default=False)

    user = db.relationship("User", back_populates="outfits")

    outfit_items = db.relationship(
        "OutfitItem",
        back_populates="outfit",
        cascade="all, delete-orphan"
    )


class OutfitItem(db.Model):
    __tablename__ = "outfit_items"

    id = db.Column(db.Integer, primary_key=True)
    outfit_id = db.Column(db.Integer, db.ForeignKey("outfits.outfit_id"), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("wardrobe_items.item_id"), nullable=False)

    outfit = db.relationship("Outfit", back_populates="outfit_items")
    item = db.relationship("WardrobeItem", back_populates="outfit_items")


class Laundry(db.Model):
    __tablename__ = "laundry"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("wardrobe_items.item_id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    # quick access relationships
    item = db.relationship("WardrobeItem")
    user = db.relationship("User")


class OutfitSuggestion(db.Model):
    __tablename__ = "outfit_suggestions"

    suggestion_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    season_id = db.Column(db.Integer, db.ForeignKey("seasons.season_id"), nullable=True)
    style_id = db.Column(db.Integer, db.ForeignKey("styles.style_id"), nullable=True)
    top_item_id = db.Column(db.Integer, db.ForeignKey("wardrobe_items.item_id"), nullable=True)
    bottom_item_id = db.Column(db.Integer, db.ForeignKey("wardrobe_items.item_id"), nullable=True)
    shoes_item_id = db.Column(db.Integer, db.ForeignKey("wardrobe_items.item_id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="outfit_suggestions")
    season = db.relationship("Season")
    style = db.relationship("Style")


