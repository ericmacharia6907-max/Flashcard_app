from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import random

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flashcards.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class Deck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    cards = db.relationship('Card', backref='deck', lazy=True, cascade='all, delete-orphan')

class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    mastered = db.Column(db.Boolean, default=False)
    deck_id = db.Column(db.Integer, db.ForeignKey('deck.id'), nullable=False)

# Create database tables
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/decks')
def decks():
    all_decks = Deck.query.all()
    return render_template('decks.html', decks=all_decks)

@app.route('/create-deck', methods=['GET', 'POST'])
def create_deck():
    if request.method == 'POST':
        deck_name = request.form['deck_name']
        new_deck = Deck(name=deck_name)
        db.session.add(new_deck)
        db.session.commit()
        return redirect(url_for('decks'))
    return render_template('create_deck.html')

@app.route('/deck/<int:deck_id>')
def view_deck(deck_id):
    deck = Deck.query.get_or_404(deck_id)
    mastered_count = sum(1 for card in deck.cards if card.mastered)
    return render_template('view_deck.html', deck=deck, mastered_count=mastered_count)

@app.route('/deck/<int:deck_id>/add-card', methods=['GET', 'POST'])
def add_card(deck_id):
    deck = Deck.query.get_or_404(deck_id)
    if request.method == 'POST':
        question = request.form['question']
        answer = request.form['answer']
        new_card = Card(question=question, answer=answer, deck_id=deck_id)
        db.session.add(new_card)
        db.session.commit()
        return redirect(url_for('view_deck', deck_id=deck_id))
    return render_template('add_card.html', deck=deck)

@app.route('/card/<int:card_id>/edit', methods=['GET', 'POST'])
def edit_card(card_id):
    card = Card.query.get_or_404(card_id)
    if request.method == 'POST':
        card.question = request.form['question']
        card.answer = request.form['answer']
        db.session.commit()
        return redirect(url_for('view_deck', deck_id=card.deck_id))
    return render_template('edit_card.html', card=card)

@app.route('/card/<int:card_id>/toggle-mastered', methods=['POST'])
def toggle_mastered(card_id):
    card = Card.query.get_or_404(card_id)
    card.mastered = not card.mastered
    db.session.commit()
    return redirect(url_for('view_deck', deck_id=card.deck_id))

@app.route('/deck/<int:deck_id>/study')
def study(deck_id):
    deck = Deck.query.get_or_404(deck_id)
    shuffle = request.args.get('shuffle', 'false')
    only_unmastered = request.args.get('unmastered', 'false')
    return render_template('study.html', deck=deck, shuffle=shuffle, only_unmastered=only_unmastered)

@app.route('/deck/<int:deck_id>/delete', methods=['POST'])
def delete_deck(deck_id):
    deck = Deck.query.get_or_404(deck_id)
    db.session.delete(deck)
    db.session.commit()
    return redirect(url_for('decks'))

@app.route('/card/<int:card_id>/delete', methods=['POST'])
def delete_card(card_id):
    card = Card.query.get_or_404(card_id)
    deck_id = card.deck_id
    db.session.delete(card)
    db.session.commit()
    return redirect(url_for('view_deck', deck_id=deck_id))

if __name__ == '__main__':
    app.run(debug=True)