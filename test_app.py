import pytest
import sys
import os
 
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
 
from app import app as flask_app
from database import init_db
 
 
@pytest.fixture
def app():
    flask_app.config['DATABASE'] = ':memory:'
    flask_app.config['TESTING'] = True
    with flask_app.app_context():
        init_db()
        yield flask_app
 
 
@pytest.fixture
def client(app):
    return app.test_client()
 
 
@pytest.fixture
def db(app):
    from database import get_db
    with app.app_context():
        yield get_db()
 
 
# Тест 1: Главная страница возвращает 200
def test_index_status_200(client):
    response = client.get('/')
    assert response.status_code == 200
 
 
# Тест 2: Добавление игрока — объект появляется в БД
def test_add_player_appears_in_db(client, app):
    response = client.post('/players/add', data={
        'name': 'Иван Тестов',
        'nickname': 'tester'
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        from database import get_db
        db = get_db()
        player = db.execute("SELECT * FROM players WHERE name = 'Иван Тестов'").fetchone()
        assert player is not None
        assert player['nickname'] == 'tester'
 
 
# Тест 3: Поиск возвращает только нужные записи
def test_search_returns_correct_player(client, app):
    with app.app_context():
        from database import get_db
        db = get_db()
        db.execute("INSERT INTO players (name, nickname) VALUES ('Артём Поиск', 'searcher')")
        db.execute("INSERT INTO players (name, nickname) VALUES ('Другой Игрок', 'other')")
        db.commit()
 
    response = client.get('/search?q=Артём')
    assert response.status_code == 200
    data = response.data.decode('utf-8')
    assert 'Артём' in data
    assert 'Другой Игрок' not in data
 
 
# Тест 4: 404 при обращении к несуществующему игроку
def test_player_not_found_returns_404(client):
    response = client.get('/players/99999')
    assert response.status_code == 404
 
 
# Тест 5: Пустое имя при добавлении игрока отклоняется
def test_add_player_empty_name_rejected(client, app):
    response = client.post('/players/add', data={
        'name': '',
        'nickname': 'ghost'
    })
    assert response.status_code == 200
    data = response.data.decode('utf-8')
    assert 'пустым' in data or 'error' in data.lower() or 'не может' in data
    with app.app_context():
        from database import get_db
        db = get_db()
        player = db.execute("SELECT * FROM players WHERE nickname = 'ghost'").fetchone()
        assert player is None
