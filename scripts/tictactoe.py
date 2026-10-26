#!/usr/bin/env python3
"""Tic-tac-toe engine behind Harsh Patadia's GitHub profile README.

How it works:
  1. A visitor clicks an empty cell in README.md. The cell is a link that
     opens a pre-filled GitHub issue titled `ttt|move|<CELL>`.
  2. The `Tic-Tac-Toe move` GitHub Action runs this script.
  3. The visitor's move is applied, the bot answers with a perfect
     minimax move (it cannot lose), README.md's board + scoreboard are
     re-rendered, state is saved to game/state.json, and a comment is
     written to game/comment.md for the workflow to post on the issue.

Env vars (set by the workflow):
  ISSUE_TITLE  e.g. "ttt|move|B2"
  PLAYER       GitHub login of the visitor who opened the issue
"""

import json
import os
import random
from functools import lru_cache
from urllib.parse import quote

CELLS = ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3"]
REPO = "harsh-patadia/harsh-patadia"
STATE_PATH = "game/state.json"
README_PATH = "README.md"
COMMENT_PATH = "game/comment.md"
START, END = "<!-- GAME:START -->", "<!-- GAME:END -->"
LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),  # rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),  # columns
    (0, 4, 8), (2, 4, 6),             # diagonals
]


def winner(board):
    for a, b, c in LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None


def minimax(board, bot_turn):
    """Perfect play: +10 bot wins, -10 visitor wins, 0 draw. (Memoized.)"""
    return _minimax(tuple(board), bot_turn)


@lru_cache(maxsize=None)
def _minimax(board, bot_turn):
    w = winner(board)
    if w == "O":
        return 10
    if w == "X":
        return -10
    if all(board):
        return 0
    scores = []
    for i in range(9):
        if not board[i]:
            nxt = board[:i] + (("O" if bot_turn else "X"),) + board[i + 1:]
            scores.append(_minimax(nxt, not bot_turn))
    return max(scores) if bot_turn else min(scores)


def bot_move(board):
    """Pick a perfect move; prefer centre/corners among equals so games vary."""
    best, moves = -100, []
    for i in range(9):
        if not board[i]:
            board[i] = "O"
            s = minimax(board, False)
            board[i] = ""
            if s > best:
                best, moves = s, [i]
            elif s == best:
                moves.append(i)
    for pref in (4, 0, 2, 6, 8):
        if pref in moves:
            return pref
    return random.choice(moves)


def issue_url(cell):
    title = quote(f"ttt|move|{cell}")
    body = quote(
        "Just hit \"Submit new issue\" - the bot will answer and redraw "
        "the board on the profile. Please don't edit the title."
    )
    return f"https://github.com/{REPO}/issues/new?title={title}&body={body}"


def board_table(board, linked=True):
    rows = []
    for r in range(3):
        cells = []
        for c in range(3):
            i = r * 3 + c
            v = board[i]
            if v == "X":
                cells.append("❌")
            elif v == "O":
                cells.append("⭕")
            elif linked:
                cells.append(f"[{CELLS[i]}]({issue_url(CELLS[i])})")
            else:
                cells.append("⬜")
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(["|   |   |   |", "|---|---|---|"] + rows)


def render(state):
    s = state["scores"]
    last = state.get("last_result")
    last_line = f"\n**Last game:** {last}\n" if last else ""
    mover = state.get("last_player")
    mover_line = f" Last move by @{mover}." if mover else ""
    return f"""{START}
### 🎮 Tic-tac-toe vs the profile bot

You're ❌. The bot is ⭕ and plays perfect tic-tac-toe — it has literally never lost a game. Click any empty cell to move: it opens an issue, just submit it, and the bot answers and redraws the board here within a minute.

{board_table(state['board'])}
{last_line}
**Scoreboard (all time):** 🧑 Visitors **{s['visitors']}** · 🤖 Bot **{s['bot']}** · 🤝 Draws **{s['draws']}** · Games finished: **{state['games_played']}**{mover_line}
{END}"""


def swap_section(text, start, end, new_block):
    i, j = text.index(start), text.index(end) + len(end)
    return text[:i] + new_block + text[j:]


def load_state():
    with open(STATE_PATH) as f:
        return json.load(f)


def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def write_comment(text):
    os.makedirs(os.path.dirname(COMMENT_PATH), exist_ok=True)
    with open(COMMENT_PATH, "w") as f:
        f.write(text)


def finish_game(state, result, player):
    """Record a finished game and reset the board for the next visitor."""
    state["games_played"] += 1
    if result == "O":
        state["scores"]["bot"] += 1
        state["last_result"] = f"🤖 The bot beat @{player}. The streak continues."
    elif result == "X":
        state["scores"]["visitors"] += 1
        state["last_result"] = (
            f"😱 @{player} BEAT THE BOT. This was supposed to be impossible — "
            "if you see this, the minimax has a bug and Harsh owes you a coffee."
        )
    else:
        state["scores"]["draws"] += 1
        state["last_result"] = (
            f"🤝 @{player} forced a draw — the best result anyone can get here."
        )
    state["board"] = [""] * 9
    state["last_player"] = player


def main():
    title = os.environ.get("ISSUE_TITLE", "")
    player = os.environ.get("PLAYER", "someone")
    parts = title.strip().split("|")
    cell = parts[2].strip().upper() if len(parts) == 3 else ""

    state = load_state()

    if cell not in CELLS:
        write_comment(
            f"🤖 I couldn't read that move (`{title}`). "
            "Click a cell on the profile instead — typing titles by hand is error-prone."
        )
        return

    idx = CELLS.index(cell)
    if state["board"][idx]:
        write_comment(
            f"🤖 Cell **{cell}** is already taken in the current game. "
            "The board on the profile is up to date — pick an empty cell."
        )
        return

    # Visitor's move.
    state["board"][idx] = "X"
    state["last_player"] = player
    w = winner(state["board"])
    if w or all(state["board"]):
        finish_game(state, w or "draw", player)
        outcome = "🎉 You won?! (See the profile — history has been made.)" if w == "X" else \
                  "🤖 The bot wins this one." if w == "O" else "🤝 It's a draw — the best anyone can do."
        board_after = state["board"]  # reset board
        save_state(state)
        with open(README_PATH) as f:
            readme = f.read()
        with open(README_PATH, "w") as f:
            f.write(swap_section(readme, START, END, render(state)))
        write_comment(
            f"You played **{cell}**. {outcome}\n\n"
            "A fresh board is already up on the profile for the next challenger."
        )
        return

    # Bot's reply.
    bidx = bot_move(state["board"])
    state["board"][bidx] = "O"
    bot_cell = CELLS[bidx]
    w = winner(state["board"])
    if w or all(state["board"]):
        final_board = list(state["board"])
        finish_game(state, w or "draw", player)
        outcome = "🤖 The bot wins this one. The board has been reset for the next challenger." if w == "O" else \
                  "🤝 A draw — the best result anyone can get. The board has been reset for the next challenger."
        save_state(state)
        with open(README_PATH) as f:
            readme = f.read()
        with open(README_PATH, "w") as f:
            f.write(swap_section(readme, START, END, render(state)))
        write_comment(
            f"You played **{cell}**, the bot answered **{bot_cell}**. {outcome}\n\n"
            f"Final board:\n\n{board_table(final_board, linked=False)}"
        )
        return

    save_state(state)
    with open(README_PATH) as f:
        readme = f.read()
    with open(README_PATH, "w") as f:
        f.write(swap_section(readme, START, END, render(state)))
    write_comment(
        f"You played **{cell}**, the bot answered **{bot_cell}**. Your turn again — "
        "the updated board is live on the profile.\n\n"
        f"{board_table(state['board'], linked=False)}"
    )


if __name__ == "__main__":
    main()
