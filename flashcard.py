from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
import random
import json
import io
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Use PostgreSQL if available, otherwise SQLite for local development
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///flashcards.db'
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
    search_query = request.args.get('search', '')
    if search_query:
        all_decks = Deck.query.filter(Deck.name.ilike(f'%{search_query}%')).all()
    else:
        all_decks = Deck.query.all()
    return render_template('decks.html', decks=all_decks, search_query=search_query)

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

@app.route('/deck/<int:deck_id>/export')
def export_deck(deck_id):
    deck = Deck.query.get_or_404(deck_id)
    
    # Create export data
    export_data = {
        'deck_name': deck.name,
        'cards': [
            {
                'question': card.question,
                'answer': card.answer,
                'mastered': card.mastered
            }
            for card in deck.cards
        ]
    }
    
    # Convert to JSON
    json_data = json.dumps(export_data, indent=2)
    
    # Create file in memory
    file = io.BytesIO()
    file.write(json_data.encode('utf-8'))
    file.seek(0)
    
    # Send file as download
    filename = f"{deck.name.replace(' ', '_')}.json"
    return send_file(file, as_attachment=True, download_name=filename, mimetype='application/json')

@app.route('/import-deck', methods=['GET', 'POST'])
def import_deck():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(url_for('import_deck'))
        
        file = request.files['file']
        
        if file.filename == '':
            return redirect(url_for('import_deck'))
        
        if file and file.filename.endswith('.json'):
            try:
                # Read and parse JSON
                data = json.load(file)
                
                # Create new deck
                new_deck = Deck(name=data['deck_name'])
                db.session.add(new_deck)
                db.session.flush()  # Get the deck ID
                
                # Add cards
                for card_data in data['cards']:
                    new_card = Card(
                        question=card_data['question'],
                        answer=card_data['answer'],
                        mastered=card_data.get('mastered', False),
                        deck_id=new_deck.id
                    )
                    db.session.add(new_card)
                
                db.session.commit()
                return redirect(url_for('decks'))
            except Exception as e:
                return f"Error importing deck: {str(e)}"
        
    return render_template('import_deck.html')

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