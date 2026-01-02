import sqlite3

def create_database():
    conn = sqlite3.connect('chinook.db')
    c = conn.cursor()

    # Create tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS artists (
            id INTEGER PRIMARY KEY,
            name TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS albums (
            id INTEGER PRIMARY KEY,
            title TEXT,
            artist_id INTEGER,
            FOREIGN KEY (artist_id) REFERENCES artists(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS tracks (
            id INTEGER PRIMARY KEY,
            name TEXT,
            album_id INTEGER,
            milliseconds INTEGER,
            FOREIGN KEY (album_id) REFERENCES albums(id)
        )
    ''')

    # Insert data
    artists = [
        (1, 'AC/DC'),
        (2, 'Accept'),
        (3, 'Aerosmith'),
        (4, 'Alanis Morissette'),
        (5, 'Alice In Chains'),
    ]
    c.executemany('INSERT OR IGNORE INTO artists VALUES (?,?)', artists)

    albums = [
        (1, 'For Those About To Rock We Salute You', 1),
        (2, 'Balls to the Wall', 2),
        (3, 'Restless and Wild', 2),
        (4, 'Let There Be Rock', 1),
        (5, 'Big Ones', 3),
    ]
    c.executemany('INSERT OR IGNORE INTO albums VALUES (?,?,?)', albums)

    tracks = [
        (1, 'For Those About To Rock (We Salute You)', 1, 343719),
        (2, 'Balls to the Wall', 2, 342562),
        (3, 'Fast as a Shark', 3, 230619),
        (4, 'Restless and Wild', 3, 252051),
        (5, 'Princess of the Dawn', 3, 375418),
    ]
    c.executemany('INSERT OR IGNORE INTO tracks VALUES (?,?,?,?)', tracks)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_database()
