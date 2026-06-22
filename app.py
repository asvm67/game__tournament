from flask import Flask, render_template, request, redirect, url_for, abort
from database import init_db, get_db
 
app = Flask(__name__)
app.config['DATABASE'] = 'tournament.db'
 
 
@app.teardown_appcontext
def close_db(error):
    import flask.globals as fg
    db = fg.g.pop('db', None)
    if db is not None:
        db.close()
 
 
@app.route('/')
def index():
    db = get_db()
    players = db.execute(
        'SELECT p.id, p.name, p.nickname, '
        'COUNT(CASE WHEN m.winner_id = p.id THEN 1 END) AS wins, '
        'COUNT(CASE WHEN (m.player1_id = p.id OR m.player2_id = p.id) THEN 1 END) AS games '
        'FROM players p '
        'LEFT JOIN matches m ON p.id = m.player1_id OR p.id = m.player2_id '
        'GROUP BY p.id '
        'ORDER BY wins DESC, games DESC'
    ).fetchall()
    recent_matches = db.execute(
        'SELECT m.id, p1.name AS p1_name, p1.nickname AS p1_nick, '
        'p2.name AS p2_name, p2.nickname AS p2_nick, '
        'w.name AS winner_name, m.played_at '
        'FROM matches m '
        'JOIN players p1 ON m.player1_id = p1.id '
        'JOIN players p2 ON m.player2_id = p2.id '
        'JOIN players w ON m.winner_id = w.id '
        'ORDER BY m.played_at DESC LIMIT 10'
    ).fetchall()
    return render_template('index.html', players=players, recent_matches=recent_matches)
 
 
@app.route('/players')
def players():
    db = get_db()
    all_players = db.execute('SELECT * FROM players ORDER BY name').fetchall()
    return render_template('players.html', players=all_players)
 
 
@app.route('/players/add', methods=['GET', 'POST'])
def add_player():
    error = None
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        nickname = request.form.get('nickname', '').strip()
        if not name:
            error = 'Имя игрока не может быть пустым.'
        else:
            db = get_db()
            db.execute('INSERT INTO players (name, nickname) VALUES (?, ?)', (name, nickname))
            db.commit()
            return redirect(url_for('players'))
    return render_template('add_player.html', error=error)
 
 
@app.route('/players/<int:player_id>')
def player_detail(player_id):
    db = get_db()
    player = db.execute('SELECT * FROM players WHERE id = ?', (player_id,)).fetchone()
    if player is None:
        abort(404)
    matches = db.execute(
        'SELECT m.id, p1.name AS p1_name, p2.name AS p2_name, '
        'w.name AS winner_name, m.played_at '
        'FROM matches m '
        'JOIN players p1 ON m.player1_id = p1.id '
        'JOIN players p2 ON m.player2_id = p2.id '
        'JOIN players w ON m.winner_id = w.id '
        'WHERE m.player1_id = ? OR m.player2_id = ? '
        'ORDER BY m.played_at DESC',
        (player_id, player_id)
    ).fetchall()
    stats = db.execute(
        'SELECT '
        'COUNT(CASE WHEN m.winner_id = ? THEN 1 END) AS wins, '
        'COUNT(CASE WHEN (m.player1_id = ? OR m.player2_id = ?) THEN 1 END) AS games '
        'FROM matches m '
        'WHERE m.player1_id = ? OR m.player2_id = ?',
        (player_id, player_id, player_id, player_id, player_id)
    ).fetchone()
    return render_template('player_detail.html', player=player, matches=matches, stats=stats)
 
 
@app.route('/matches/add', methods=['GET', 'POST'])
def add_match():
    db = get_db()
    players_list = db.execute('SELECT * FROM players ORDER BY name').fetchall()
    error = None
    if request.method == 'POST':
        p1_id = request.form.get('player1_id')
        p2_id = request.form.get('player2_id')
        winner_id = request.form.get('winner_id')
        if not p1_id or not p2_id or not winner_id:
            error = 'Заполните все поля.'
        elif p1_id == p2_id:
            error = 'Игроки должны быть разными.'
        elif winner_id not in (p1_id, p2_id):
            error = 'Победитель должен быть одним из участников матча.'
        else:
            db.execute(
                'INSERT INTO matches (player1_id, player2_id, winner_id) VALUES (?, ?, ?)',
                (p1_id, p2_id, winner_id)
            )
            db.commit()
            return redirect(url_for('index'))
    return render_template('add_match.html', players=players_list, error=error)
 
 
@app.route('/matches/<int:match_id>/delete', methods=['POST'])
def delete_match(match_id):
    db = get_db()
    match = db.execute('SELECT * FROM matches WHERE id = ?', (match_id,)).fetchone()
    if match is None:
        abort(404)
    db.execute('DELETE FROM matches WHERE id = ?', (match_id,))
    db.commit()
    return redirect(url_for('index'))
 
 
@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    db = get_db()
    players_found = []
    if query:
        players_found = db.execute(
            'SELECT p.id, p.name, p.nickname, '
            'COUNT(CASE WHEN m.winner_id = p.id THEN 1 END) AS wins, '
            'COUNT(CASE WHEN (m.player1_id = p.id OR m.player2_id = p.id) THEN 1 END) AS games '
            'FROM players p '
            'LEFT JOIN matches m ON p.id = m.player1_id OR p.id = m.player2_id '
            'WHERE p.name LIKE ? OR p.nickname LIKE ? '
            'GROUP BY p.id',
            (f'%{query}%', f'%{query}%')
        ).fetchall()
    return render_template('search.html', players=players_found, query=query)
 
 
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404
 
 
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
