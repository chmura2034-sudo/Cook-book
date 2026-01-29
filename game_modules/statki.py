import uuid

BOARD_SIZE = 10

# Pamięć gry
statki_challenges = {}   # cid -> {id, from_id, to_id, status}
statki_games = {}        # cid -> {boards, hits, turn, logs, winner, moves}


def empty_board():
    return [["." for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]


def place_dummy_ships(board):
    # Proste statki demo
    for i in range(3):
        board[1][i+1] = "S"
    for i in range(4):
        board[4][i+3] = "S"
    for i in range(2):
        board[7][i+5] = "S"


def create_challenge(current_user, opponent):
    cid = str(uuid.uuid4())
    statki_challenges[cid] = {
        "id": cid,
        "from_id": current_user.id,
        "from_username": current_user.username,
        "to_id": opponent.id,
        "to_username": opponent.username,
        "status": "pending"
    }
    return cid


def accept_challenge(cid):
    ch = statki_challenges[cid]
    ch["status"] = "accepted"

    b1 = empty_board()
    b2 = empty_board()
    place_dummy_ships(b1)
    place_dummy_ships(b2)

    statki_games[cid] = {
        "boards": {
            ch["from_id"]: b1,
            ch["to_id"]: b2
        },
        "hits": {
            ch["from_id"]: [],
            ch["to_id"]: []
        },
        "turn": ch["from_id"],
        "logs": [f"Gra rozpoczęta: {ch['from_username']} vs {ch['to_username']}"],
        "winner": None,
        "moves": []
    }


def get_state(cid, player_id):
    game = statki_games[cid]
    ch = statki_challenges[cid]

    opponent_id = ch["to_id"] if player_id == ch["from_id"] else ch["from_id"]

    my_board = game["boards"][player_id]
    opp_board = game["boards"][opponent_id]

    fog = [["" for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            if opp_board[y][x] == "X":
                fog[y][x] = "X"
            elif opp_board[y][x] == "O":
                fog[y][x] = "O"

    return {
        "my_board": my_board,
        "target_board": fog,
        "logs": game["logs"],
        "turn": game["turn"],
        "winner": game["winner"]
    }


def make_move(cid, player_id, x, y):
    game = statki_games[cid]
    ch = statki_challenges[cid]

    if game["winner"]:
        return "finished"

    if game["turn"] != player_id:
        return "not your turn"

    opponent_id = ch["to_id"] if player_id == ch["from_id"] else ch["from_id"]
    board = game["boards"][opponent_id]

    cell = board[y][x]
    result = "miss"

    if cell == "S":
        board[y][x] = "X"
        result = "hit"
    elif cell in ["X", "O"]:
        return "already"
    else:
        board[y][x] = "O"

    game["moves"].append({"by": player_id, "x": x, "y": y, "result": result})
    game["logs"].append(f"Gracz {player_id} strzela w ({x+1},{y+1}) → {result}")

    # Sprawdź zwycięstwo
    if not any("S" in row for row in board):
        game["winner"] = player_id
        game["logs"].append(f"Gracz {player_id} wygrał!")

    if not game["winner"]:
        game["turn"] = opponent_id

    return "ok"
