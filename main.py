import numpy as np

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum, IntEnum, auto
from os import system, name
from random import shuffle
from string import ascii_uppercase
from sys import exit
from tinydb import TinyDB, Query
from typing import TypeVar, TypedDict, Unpack
from yaml import safe_load


class Msg(StrEnum):
    CHOICE_MSG = "Quitter et sauvegarder -> quit\nChoisis une carte à retourner (exemple B1): "
    ERROR_MSG = "On ne peut pas retourner deux fois la même carte !"
    GAME_WIN_MSG = "Tu as trouvé la paire, bravo !"
    GAME_LOSE_MSG = "Ce n'est pas un match, mémorise les emplacements et retente ta chance"
    LVL_MSG  = "\nBravo ! Tu as terminé le level "
    CONTINUE_MSG = "Appuies sur une touche pour continuer"
    NO_LOAD_MSG  = "\nIl n'y a aucune partie à charger"
    END_MSG  = "Plus de coups disponible la partie est fini !"
    LOAD_MSG  = "Taper le numéro de la partie à charger :"
    MENU_MSG = "\nBienvenue dans le jeu de Memory !\n1) Nouveau jeu\n2) Charger\nVotre choix: "
    PSEUDO_MSG = "\nVotre pseudo: "
    MODE_MSG = "Mode:\n1) Facile\n2) Difficile\nVotre choix: "


class Keys(IntEnum):
    LEVEL = 0
    RECTO = auto()
    VERSO = auto()
    BDD =  auto()


class PlayerCharacteristics(TypedDict):
    Joueur : str
    Level : int
    Mode : str
    Points : int
    Level_points : int
    Tables : list
 
 
class BackUp:
    def __init__(self, bdd:str) -> None:
        self.db = TinyDB(bdd, indent=4)

    def save(self, state:Unpack[PlayerCharacteristics], name:str) -> None:
        Game = Query()
        if self.db.table("SAVES").search(Game.Joueur.matches(name)):
            self.db.table("SAVES").update(state._content, Game.Joueur == name)
        else:
            self.db.table("SAVES").insert(state._content)

    def load(self, index:str) -> dict:
        return self.db.table("SAVES").get(doc_id=index)

@dataclass
class Player:
    pseudo : str
    level  : int
    mode : str
    points : int = 0
    level_points : int = 0

        
class Memo:   
    TPlayer = TypeVar("TPlayer", bound="Player")
    TState = TypeVar("TState", bound="_GameState")
           
    @dataclass
    class _GameState: 
        _content : dict
            
        @property
        def get_content(self) -> dict:
            return self._content
        
        
    CONFIG_FILE = "configuration.yml"
    KEYS = ("level", "recto", "verso", "bdd")
    MODE = ("Facile", "Difficile")
    X_COORD = ascii_uppercase[:10]
    
    def __init__(self) -> None:
        self._data : dict  = self._load_data(Memo.CONFIG_FILE)
        self._LEVEL : tuple = tuple(self._data[Memo.KEYS[Keys.LEVEL]])
        self._RECTO : list= self._data[Memo.KEYS[Keys.RECTO]]
        self._VERSO : str = self._data[Memo.KEYS[Keys.VERSO]]
        self._DB : str = self._data[Memo.KEYS[Keys.BDD]]
        self.back_up = BackUp(self._DB)
        self.load_list : list = [game for game in self.back_up.db.table("SAVES")]
        self.tables : list = [None, None]

    def __call__(self) -> None:
        self._clear_screen()
        self._game_loop()
        
    def _choice_game(self, choice:str) -> tuple:
        while (choice == ""\
        or 0 > len(choice) >= 3 \
        or not choice[1:].isdigit()\
        or (choice[0].upper() not in Memo.X_COORD[0:self._LEVEL[self.player.level]])\
        or (int(choice[1:]) not in range(1, self._LEVEL[self.player.level] + 1))\
        or self.tables[1][int(choice[1:]) - 1, Memo.X_COORD.index(choice[0].upper())] != self._VERSO)\
        and choice.lower() != "quit":
            choice = input(Msg.CHOICE_MSG)
            
        if choice == "quit":
            self.back_up.save(self._create_save(), self.player.pseudo)
            exit()
        return int(choice[1:]) - 1, Memo.X_COORD.index(choice[0].upper()) 
  
    def _clear_screen(self):
        system('cls' if name == 'nt' else 'clear')
              
    def _create_game_data(self, tables:list=[None, None]) -> None:
        level = self.player.level
        mode = self.player.mode == Memo.MODE[0]
        self.max_chance = (self._LEVEL[level] * 2 if mode else self._LEVEL[level]) * self._LEVEL[level] + (1 if level else 0)
        self.tables = tables
        
        if not self.tables[0]:
            self.tables[0] = self._RECTO[:self._LEVEL[level]**2 // 2 ] * 2
            shuffle(self.tables[0])
            self.tables[1] = [self._VERSO for _ in range(self._LEVEL[level]**2)]

        for index in range(len(self.tables)):    
            self.tables[index] = np.array([self.tables[index][i:i+self._LEVEL[level]] for i in range(0,len(self.tables[index]),self._LEVEL[level])])
 
    def _create_new_player(self) -> TPlayer:
        pseudo = input(Msg.PSEUDO_MSG)
        level = 0
        mode = self._verify_input(Msg.MODE_MSG)
        mode = Memo.MODE[0] if not int(mode) - 1 else Memo.MODE[1]
        return Player(pseudo, level, mode)

    def _create_save(self) -> TState:
        self._content = PlayerCharacteristics({"Joueur" : self.player.pseudo,
                                               "Level" : self.player.level,
                                               "Mode" : self.player.mode,
                                               "Points" : self.player.points,
                                               "Level_points" : self.player.level_points,
                                               "Tables" : [list(np.concatenate(table)) for table in self.tables]
                                               })
        return Memo._GameState(self._content)
          
    def _display_menu(self) -> None:
        menu_choice = self._verify_input(Msg.MENU_MSG)
        if not int(menu_choice) - 1 or not self.load_list:
            print(Msg.NO_LOAD_MSG) if not self.load_list and int(menu_choice) - 1 else ...
            self.player = self._create_new_player()
        else:
            self.player = self._load_data_player()
        self._create_game_data(self.tables)
                
    def _display_table_game(self, table:np.ndarray) -> None:
        self._clear_screen()
        compteur = 1
        game = f"{self.player.pseudo} - Total points: {self.player.points}\nLevel: {self.player.level} | Level points: {self.player.level_points}\nMode: {self.player.mode}\nCoups restants : {self.max_chance}\n\n\n"
        game += f"    {'  '.join(Memo.X_COORD[:self._LEVEL[self.player.level]])}\n\n"
        for i in table:
            game += f"{compteur:>2} {' '.join(i)}\n\n"
            compteur += 1
        print(game)
    
    def _game_analysis(self, choice_list:list, gaming_table:np.ndarray) -> str:
        if choice_list[0] == choice_list[1]:
            message = Msg.ERROR_MSG   
        elif self.tables[0][*choice_list[0]] == self.tables[0][*choice_list[1]]:
            message = Msg.GAME_WIN_MSG
            self.tables[1] = np.copy(gaming_table)
            if self._VERSO not in list(np.concatenate(self.tables[1])):
                message += f"{Msg.LVL_MSG}{self.player.level}"
                self._lvl_up()
        else:
            message = Msg.GAME_LOSE_MSG
        return message
        
    def _game_loop(self) -> None:
        self._display_menu()
        while True:
            if not self.max_chance: exit(Msg.END_MSG)
            
            message = self._play()
            self.player.points += 1
            self.player.level_points += 1
            self.max_chance -= 1
            print(message)
            input(Msg.CONTINUE_MSG)   
    
    def _load_data_player(self) -> TPlayer:
        print("".join(f"{index}) Joueur: {elem['Joueur']}, level {elem['Level']}, mode: {elem['Mode']}, points: {elem['Points']}, \
level_points: {elem['Level_points']}\n" for index, elem in enumerate(self.load_list, 1)))
        load_choice = self._verify_input(Msg.LOAD_MSG)
        player_load = self._restore(load_choice)
        player_load = list(player_load.values())
        self.tables = player_load[-1]
        return Player(*player_load[0:5])
    
    def _load_data(self, config:str) -> dict:
        with open(config, mode="r", encoding="utf-8") as f:
            return safe_load(f)
          
    def _lvl_up(self) -> None:
        self.player.level += 1
        self.player.level_points = -1
        self._create_game_data()
        
    def _play(self) -> None:   
        gaming_table = np.copy(self.tables[1])
        choice_list = []
        self._display_table_game(gaming_table)

        while len(choice_list) != 2:
            choice = self._choice_game(input(Msg.CHOICE_MSG))    
            choice_list.append(choice)
            gaming_table[*choice] = self.tables[0][*choice]
            self._display_table_game(gaming_table)
        
        return self._game_analysis(choice_list, gaming_table)

    def _restore(self,index:int) -> Callable:
        return self.back_up.load(index)
  
    def _verify_input(self, message:str) -> str:
        load = message == Msg.LOAD_MSG
        while True:
            self._clear_screen() if not load else ...
            try: choice = int(input(message))
            except ValueError: continue
            if (load and 0 < choice <= len(self.load_list)) or (not load and 0 < choice < 3): return choice
                
if __name__ == "__main__":
    jeu = Memo()
    jeu()