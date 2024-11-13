import pytest
import random
import logging
from titan.tiny_service.events import (
    Event,
    EventTranslatorException,
    EventTranslatorMachineContext,
    EventTranslatorMachineState,
    EventTranslatorMachine,
)
from titan.tiny_service.model import (
    ModelException,
    Model
)
from tests.titan.tiny_service.events import tictactoe_player_events
from tests.titan.tiny_service.events import tictactoe_umpire_events

logger = logging.getLogger(__name__)



################################
##
## Various routines for generating test data
##
################################

def update_board(board, player_event):
    if isinstance(player_event, tictactoe_player_events.PlayerXPlacedChipEvent):
        board[player_event.col()][player_event.row()] = 'X'
    elif isinstance(player_event, tictactoe_player_events.PlayerOPlacedChipEvent):
        board[player_event.col()][player_event.row()] = 'O'
    return board

def find_winning_player(board):
    if board[0][0] == board[0][1] == board[0][2] != '?':
        return board[0][0]
    elif board[1][0] == board[1][1] == board[1][2] != '?':
        return board[1][0]
    elif board[2][0] == board[2][1] == board[2][2] != '?':
        return board[2][0]
    elif board[0][0] == board[1][0] == board[2][0] != '?':
        return board[0][0]
    elif board[0][1] == board[1][1] == board[2][1] != '?':
        return board[0][1]
    elif board[0][2] == board[1][2] == board[2][2] != '?':
        return board[0][2]
    elif board[0][0] == board[1][1] == board[2][2] != '?':
        return board[0][0]
    elif board[0][2] == board[1][1] == board[2][0] != '?':
        return board[0][2]
    raise ValueError("There is no winning player in this board")


def is_game_over(board, player_events):
    if player_events == []:
        return False
    elif isinstance(player_events[-1], (    tictactoe_player_events.PlayerXShookBoardInAngerEvent,
                                            tictactoe_player_events.PlayerOShookBoardInAngerEvent  )):
        return True
    else:
        try:
            winning_player = find_winning_player(board)
            return True
        except ValueError:
            return (len(player_events) == 9)


def random_tictactoe_move(rng, board, player):
    def available_spots(board):
        return {(x,y) for x in range(3) for y in range(3) if board[x][y] == '?'}

    if rng.random() < 0.1:
        # sometimes players get angry :P
        if player == 'X':
            return tictactoe_player_events.PlayerXShookBoardInAngerEvent.create()
        else:
            return tictactoe_player_events.PlayerOShookBoardInAngerEvent.create()
    else:
        spot = rng.choice(list(available_spots(board)))
        if player == 'X':
            return tictactoe_player_events.PlayerXPlacedChipEvent.create(col=spot[0], row=spot[1])
        else:
            return tictactoe_player_events.PlayerOPlacedChipEvent.create(col=spot[0], row=spot[1])


def create_player_events_for_game(rng):
    """Generate the player events for one game of tic tac toe"""
    result = []
    board = [['?', '?', '?'], ['?', '?', '?'], ['?', '?', '?']]
    cur_player_index = rng.choice([0, 1])
    while not is_game_over(board, result):
        cur_player = ['X', 'O'][cur_player_index]
        player_event = random_tictactoe_move(rng, board, cur_player)
        update_board(board, player_event)
        result.append(player_event)
        cur_player_index = (cur_player_index + 1) % 2 
    return result




def create_umpire_events_for_game(player_events, x_score: int, o_score: int):
    """Generate the 'target' umpire events for the player events of one tictactoe game"""
    result = []
    board = [['?', '?', '?'], ['?', '?', '?'], ['?', '?', '?']]
    for event in player_events:
        update_board(board, event)

    if isinstance(player_events[-1], tictactoe_player_events.PlayerXShookBoardInAngerEvent):
        return [    tictactoe_umpire_events.PlayerOWonGameEvent.create(),
                    tictactoe_umpire_events.ScoreboardWasUpdatedEvent.create(x_score=x_score, o_score=o_score+1)   ]
    elif isinstance(player_events[-1], tictactoe_player_events.PlayerOShookBoardInAngerEvent):
        return [    tictactoe_umpire_events.PlayerXWonGameEvent.create(),
                    tictactoe_umpire_events.ScoreboardWasUpdatedEvent.create(x_score=x_score+1, o_score=o_score)   ]
    else:        
        try:
            winning_player = find_winning_player(board)
            if winning_player == 'X':
                return [    tictactoe_umpire_events.PlayerXWonGameEvent.create(),
                            tictactoe_umpire_events.ScoreboardWasUpdatedEvent.create(x_score=x_score+1, o_score=o_score)   ]
            elif winning_player == 'O':
                return [    tictactoe_umpire_events.PlayerOWonGameEvent.create(),
                            tictactoe_umpire_events.ScoreboardWasUpdatedEvent.create(x_score=x_score, o_score=o_score+1)   ]
            else:
                raise RuntimeError(f"Unexpected winner `{winning_player}`")
        except ValueError:
            # draw
            return [tictactoe_umpire_events.NeitherPlayerWonGameEvent.create()]


def create_player_and_umpire_events(rng, num_games: int):
    """Create some test data that we can use in order to test our Event Translator Machines"""
    result = ([], [])
    x_score = 0
    o_score = 0
    for _ in range(num_games):
        player_events = create_player_events_for_game(rng)
        umpire_events = create_umpire_events_for_game(player_events, x_score, o_score)
        if isinstance(umpire_events[-1], tictactoe_umpire_events.ScoreboardWasUpdatedEvent):
            x_score = umpire_events[-1].x_score()
            o_score = umpire_events[-1].o_score()

        result[0].extend(player_events)
        result[1].extend(umpire_events)
    return result




################################
##
## Event Translation Machine
##
################################


class UmpireModel(Model):
    def __init__(self, x_score: int, o_score: int):
        self._x_score = x_score
        self._o_score = o_score

    def x_score(self):
        return self._x_score

    def o_score(self):
        return self._o_score

    def _inc_x_score(self):
        self._x_score += 1

    def _inc_o_score(self):
        self._o_score += 1

    def process_event(self, event: Event):
        if isinstance(event, tictactoe_umpire_events.PlayerXWonGameEvent):
            self._inc_x_score()
        elif isinstance(event, tictactoe_umpire_events.PlayerOWonGameEvent):
            self._inc_o_score()          

    def clone(self):
        return self.__class__(x_score=self.x_score(), o_score=self.o_score())


class PlayerModel(Model):
    def __init__(self, placed_chips: set):
        self._placed_chips = placed_chips

    def placed_chips(self):
        return self._placed_chips

    def _place_new_chip(self, x, y, chip):
        self._placed_chips.add((x, y, chip))

    def _reset_for_new_game(self):
        self._placed_chips = set()

    def is_winning_move(self, player, x, y):
        new_placed_chips = self.placed_chips() | {(x, y, player)}
        if {(0, 0, player), (0, 1, player), (0, 2, player)}.issubset(new_placed_chips):
            return True
        elif {(1, 0, player), (1, 1, player), (1, 2, player)}.issubset(new_placed_chips):
            return True
        elif {(2, 0, player), (2, 1, player), (2, 2, player)}.issubset(new_placed_chips):
            return True
        elif {(0, 0, player), (1, 0, player), (2, 0, player)}.issubset(new_placed_chips):
            return True
        elif {(0, 1, player), (1, 1, player), (2, 1, player)}.issubset(new_placed_chips):
            return True
        elif {(0, 2, player), (1, 2, player), (2, 2, player)}.issubset(new_placed_chips):
            return True
        elif {(0, 0, player), (1, 1, player), (2, 2, player)}.issubset(new_placed_chips):
            return True
        elif {(0, 2, player), (1, 1, player), (2, 0, player)}.issubset(new_placed_chips):
            return True
        return False

    def is_last_move(self):
        return len(self.placed_chips()) == 8

    def is_board_full(self):
        return len(self.placed_chips()) == 9

    def is_valid_move(self, x, y):
        return (    ((x, y, 'X') not in self.placed_chips()) and 
                    ((x, y, 'O') not in self.placed_chips()) and
                    x>=0 and x<=2 and
                    y>=0 and y<=2 and
                    not self.is_board_full()    )

    def process_event(self, event: Event):
        if isinstance(event, tictactoe_player_events.PlayerOPlacedChipEvent):
            self._place_new_chip(event.col(), event.row(), 'O')
        elif isinstance(event, tictactoe_player_events.PlayerXPlacedChipEvent):
            self._place_new_chip(event.col(), event.row(), 'X')

    def clone(self):
        return self.__class__(set(self.placed_chips()))


class PlayerEventTranslatorContext(EventTranslatorMachineContext):
    def __init__(self, player_model: PlayerModel, umpire_model: UmpireModel):
        self._player_model = player_model
        self._umpire_model = umpire_model

    def player_model(self):
        return self._player_model

    def umpire_model(self):
        return self._umpire_model

    def reset_for_new_game(self):
        self._player_model = PlayerModel(set())

    def clone(self):
        return self.__class__(player_model=self.player_model().clone(), umpire_model=self.umpire_model().clone())

    @classmethod
    def create_new(cls):
        return cls(player_model=PlayerModel(set()), umpire_model=UmpireModel(x_score=0, o_score=0))




class PlayerEventTranslator(EventTranslatorMachine):

    class WaitingForGameToStartState(EventTranslatorMachineState):
        @classmethod
        def next_state(cls, context: PlayerEventTranslatorContext, event: Event):
            if isinstance(event, (  tictactoe_player_events.PlayerXShookBoardInAngerEvent,
                                    tictactoe_player_events.PlayerOShookBoardInAngerEvent)):
                return cls
            elif isinstance(event, tictactoe_player_events.PlayerOPlacedChipEvent):
                if not context.player_model().is_valid_move(event.col(), event.row()):
                    raise EventTranslatorException(f"Invalid move for event: {event}")
                return PlayerEventTranslator.WaitingForPlayerXState
            elif isinstance(event, tictactoe_player_events.PlayerXPlacedChipEvent):
                if not context.player_model().is_valid_move(event.col(), event.row()):
                    raise EventTranslatorException(f"Invalid move for event: {event}")
                return PlayerEventTranslator.WaitingForPlayerOState
            else:
                return cls

        @classmethod
        def next_context(cls, next_state: EventTranslatorMachineState, context: PlayerEventTranslatorContext, event: Event):
            if isinstance(event, tictactoe_umpire_events.EVENT_TYPES):
                result = context.clone()
                result.umpire_model().process_event(event)
                return result
            else:
                result = context.clone()
                result.player_model().process_event(event)
                return result



        @classmethod
        def translate_event(cls, next_state: EventTranslatorMachineState, context: EventTranslatorMachineContext, next_context: EventTranslatorMachineContext, event: Event):
            if isinstance(event, tictactoe_player_events.PlayerXShookBoardInAngerEvent):
                return [    tictactoe_umpire_events.PlayerOWonGameEvent.create(),
                            tictactoe_umpire_events.ScoreboardWasUpdatedEvent.create(x_score=next_context.umpire_model().x_score(), o_score=next_context.umpire_model().o_score() + 1)   ]
            elif isinstance(event, tictactoe_player_events.PlayerOShookBoardInAngerEvent):
                return [    tictactoe_umpire_events.PlayerXWonGameEvent.create(),
                            tictactoe_umpire_events.ScoreboardWasUpdatedEvent.create(x_score=next_context.umpire_model().x_score() + 1, o_score=next_context.umpire_model().o_score())   ]
            else:
                return []


    class WaitingForPlayerXState(EventTranslatorMachineState):
        @classmethod
        def next_state(cls, context: PlayerEventTranslatorContext, event: Event):
            if isinstance(event, (  tictactoe_player_events.PlayerOShookBoardInAngerEvent,
                                    tictactoe_player_events.PlayerOPlacedChipEvent)):
                raise EventTranslatorException(f"Unexpected event `{event}` in state `{cls}`")
            elif isinstance(event, tictactoe_player_events.PlayerXShookBoardInAngerEvent):
                return PlayerEventTranslator.WaitingForGameToStartState
            elif isinstance(event, tictactoe_player_events.PlayerXPlacedChipEvent):
                if not context.player_model().is_valid_move(event.col(), event.row()):
                    raise EventTranslatorException(f"Player X tried to make an invalid move: {event}")
                if context.player_model().is_winning_move('X', event.col(), event.row()):
                    return PlayerEventTranslator.WaitingForGameToStartState
                elif context.player_model().is_last_move():
                    return PlayerEventTranslator.WaitingForGameToStartState
                else:
                    return PlayerEventTranslator.WaitingForPlayerOState
            else:
                return cls

        @classmethod
        def next_context(cls, next_state: EventTranslatorMachineState, context: PlayerEventTranslatorContext, event: Event):
            if isinstance(event, tictactoe_umpire_events.EVENT_TYPES):
                result = context.clone()
                result.umpire_model().process_event(event)
                return result
            elif next_state == PlayerEventTranslator.WaitingForGameToStartState:
                result = context.clone()
                result.reset_for_new_game()
                return result
            else:
                result = context.clone()
                result.player_model().process_event(event)
                return result


        @classmethod
        def translate_event(cls, next_state: EventTranslatorMachineState, context: EventTranslatorMachineContext, next_context: EventTranslatorMachineContext, event: Event):           
            if isinstance(event, tictactoe_player_events.PlayerXShookBoardInAngerEvent):
                return [    tictactoe_umpire_events.PlayerOWonGameEvent.create(),
                            tictactoe_umpire_events.ScoreboardWasUpdatedEvent.create(x_score=next_context.umpire_model().x_score(), o_score=next_context.umpire_model().o_score() + 1)   ]
            elif isinstance(event, tictactoe_player_events.PlayerXPlacedChipEvent):
                if context.player_model().is_winning_move('X', event.col(), event.row()):
                    return [    tictactoe_umpire_events.PlayerXWonGameEvent.create(),
                                tictactoe_umpire_events.ScoreboardWasUpdatedEvent.create(x_score=next_context.umpire_model().x_score() + 1, o_score=next_context.umpire_model().o_score())   ]
                elif context.player_model().is_last_move():
                    return [tictactoe_umpire_events.NeitherPlayerWonGameEvent.create()]
            return []



    class WaitingForPlayerOState(EventTranslatorMachineState):
        @classmethod
        def next_state(cls, context: PlayerEventTranslatorContext, event: Event):
            if isinstance(event, (  tictactoe_player_events.PlayerXShookBoardInAngerEvent,
                                    tictactoe_player_events.PlayerXPlacedChipEvent)):
                raise EventTranslatorException(f"Unexpected event `{event}` in state `{cls}`")
            elif isinstance(event, tictactoe_player_events.PlayerOShookBoardInAngerEvent):
                return PlayerEventTranslator.WaitingForGameToStartState
            elif isinstance(event, tictactoe_player_events.PlayerOPlacedChipEvent):
                if not context.player_model().is_valid_move(event.col(), event.row()):
                    raise EventTranslatorException(f"Player O tried to make an invalid move: {event}")
                if context.player_model().is_winning_move('O', event.col(), event.row()):
                    return PlayerEventTranslator.WaitingForGameToStartState
                elif context.player_model().is_last_move():
                    return PlayerEventTranslator.WaitingForGameToStartState
                else:
                    return PlayerEventTranslator.WaitingForPlayerXState
            else:
                return cls

        @classmethod
        def next_context(cls, next_state: EventTranslatorMachineState, context: PlayerEventTranslatorContext, event: Event):
            if isinstance(event, tictactoe_umpire_events.EVENT_TYPES):
                result = context.clone()
                result.umpire_model().process_event(event)
                return result
            elif next_state == PlayerEventTranslator.WaitingForGameToStartState:
                result = context.clone()
                result.reset_for_new_game()
                return result
            else:
                result = context.clone()
                result.player_model().process_event(event)
                return result

        @classmethod
        def translate_event(cls, next_state: EventTranslatorMachineState, context: EventTranslatorMachineContext, next_context: EventTranslatorMachineContext, event: Event):
            if isinstance(event, tictactoe_player_events.PlayerOShookBoardInAngerEvent):
                return [    tictactoe_umpire_events.PlayerXWonGameEvent.create(),
                            tictactoe_umpire_events.ScoreboardWasUpdatedEvent.create(x_score=next_context.umpire_model().x_score() + 1, o_score=next_context.umpire_model().o_score())   ]
            elif isinstance(event, tictactoe_player_events.PlayerOPlacedChipEvent):
                if context.player_model().is_winning_move('O', event.col(), event.row()):
                    return [    tictactoe_umpire_events.PlayerOWonGameEvent.create(),
                                tictactoe_umpire_events.ScoreboardWasUpdatedEvent.create(x_score=next_context.umpire_model().x_score(), o_score=next_context.umpire_model().o_score() + 1)   ]
                elif context.player_model().is_last_move():
                    return [tictactoe_umpire_events.NeitherPlayerWonGameEvent.create()]
            return []


    def __init__(self):
        super().__init__(PlayerEventTranslator.WaitingForGameToStartState, PlayerEventTranslatorContext.create_new())



################################
##
## Pytest routines
##
################################


def test_event_translator_machine():
    rng = random.Random(42)
    player_events, target_umpire_events = create_player_and_umpire_events(rng, 300)

    # do the translation
    event_translator_machine = PlayerEventTranslator()
    translated_events = []
    for player_event in player_events:
        translated_events.extend(event_translator_machine.translate_event(player_event))

    # make sure translation matches our target
    assert len(translated_events) == len(target_umpire_events)
    for umpire_event, target_umpire_event in zip(translated_events, target_umpire_events):
        assert type(umpire_event) == type(target_umpire_event)
        # ignore the event-id which will be unique
        assert tuple(umpire_event[1:]) == tuple(target_umpire_event[1:])

