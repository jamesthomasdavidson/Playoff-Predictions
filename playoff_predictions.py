from bs4 import BeautifulSoup
from urllib.request import urlopen
from datetime import date, timedelta
import os, operator, copy, csv, sys
import numpy as np

#stores information for a game
class Game(object):

    def __init__(self, date, winner, w_score, loser, l_score, ot):
        self._date = date
        self._winner = winner
        self._w_score = w_score
        self._loser = loser
        self._l_score = l_score
        self._ot = ot

    @property
    def date(self):
        return self._date

    @property
    def winner(self):
        return self._winner

    @property
    def w_score(self):
        return self._w_score

    @property
    def loser(self):
        return self._loser

    @property
    def l_score(self):
        return self._l_score

    @property
    def ot(self):
        return self._ot

#stores information for a team
class Team(object):

    def __init__(self, team_name):
        self._points = 0
        self._games = 0
        self._name = team_name
        self._rating = ts.Rating()

    @property
    def name(self):
        return self._name

    @property
    def points(self):
        return self._points

    @points.setter
    def points(self, points):
        self._points = points

    @property
    def games(self):
        return self._games

    @games.setter
    def games(self, count):
        self._games = count

    @property
    def rating(self):
        return self._rating

    @rating.setter
    def rating(self, rating):
        self._rating = rating

#class manager for the team object.  setup() stores a static
#reference of all teams and their ranking.  when instantiating a teams
#object, it stores a list of all the team names specified.
#when you call get(), it returns a list of references to all
#the static team objects that of the specified name
class Teams(object):

    #start state is used incase we want to try multiple branches of statistical analysis
    setup_complete = False
    all_teams = []

    @staticmethod
    def setup(games):
        teams = {}
        for game in games:
            if game.winner not in teams: teams[game.winner] = Team(game.winner)
            if game.loser not in teams: teams[game.loser] = Team(game.loser)
            teams[game.winner].points += 2
            teams[game.loser].points += (1 if game.ot != 'n/a' else 0)
            teams[game.winner].games += 1
            teams[game.loser].games += 1
            teams[game.winner].rating, teams[game.loser].rating = ts.rate_1vs1(teams[game.winner].rating, teams[game.loser].rating,
                                                                               drawn=(False if game.ot == 'n/a' else True))
        Teams.all_teams = list(teams.values())
        Teams.setup_complete = True
        Teams.rank()

    @staticmethod
    def all():
        return Teams.all_teams

    @staticmethod
    def rank(key = 'mu'):
        if key == 'points':
            Teams.all_teams.sort(key=lambda x: (x.points, x.games), reverse = True)
        elif key == 'mu':
            Teams.all_teams.sort(key=lambda x: x.rating.mu, reverse = True)
        elif key == 'sigma':
            Teams.all_teams.sort(key=lambda x: x.rating.sigma, reverse = True)

    def __init__(self, team_names, name = '', n = None):
        assert(Teams.setup_complete)
        if n is not None:
            self._teams = team_names[:n]
        else:
            self._teams = team_names
        self._name = name

    #orders t1, t2 according to the current Rank() sorting
    @staticmethod
    def order(t1, t2):
        if Teams.all_teams.index(t1) < Teams.all_teams.index(t2):
            return t1, t2
        else:
            return t2, t1

    @property
    def name(self):
        return self._name

    #prints out to the screen
    def out(self):
        if self._name != '':
            print(self._name + '\n')
        for team in self.list():
            print('Team: %-25s |  mean: %-.2f  |  std: %-.2f  |  Points: %3d  |  Games: %3d' %
                (team.name, team.rating.mu, team.rating.sigma, team.points, team.games))
        print('\n'),

    #returns all of the team objects in a list
    def list(self, key = None, i = 0, n = None):
        if key is not None: Teams.rank(key)
        teams = []
        for team in Teams.all_teams:
            if team.name in self._teams:
                teams.append(team)
        if n is not None:
            teams = teams[i:n+i]
        return teams

    @property
    def first(self):
        assert(len(self.list()) > 0)
        return self.list()[0]

    @property
    def second(self):
        assert(len(self.list()) > 1)
        return self.list()[1]

    @property
    def third(self):
        assert(len(self.list()) > 2)
        return self.list()[2]

    #returns all team names
    def names(self, key = None, i = 0, n = None):
        if key is not None: Teams.rank(key)
        teams = []
        for team in Teams.all_teams:
            if team.name in self._teams:
                teams.append(team.name)
        if n is not None:
            teams = teams[i:n+i]
        return teams

    #returns a subset of a list
    def subset(self, key = None, i = 0, n = None):
        return Teams(self.names(i = i, n = n))

    def complement(self, team_names):
        names = []
        for name in team_names:
            if name not in self.names():
                names.append(name)
        return Teams(names)

#used to predict playoffs
class Playoffs(object):

    #eastern conference final
    Metropolitan = ['Washington Capitals',
                    'Columbus Blue Jackets',
                    'Pittsburgh Penguins',
                    'New York Rangers',
                    'New York Islanders',
                    'Philadelphia Flyers',
                    'Carolina Hurricanes',
                    'New Jersey Devils']

    Atlantic = ['Montreal Canadiens',
                    'Ottawa Senators',
                    'Boston Bruins',
                    'Toronto Maple Leafs',
                    'Tampa Bay Lightning',
                    'Florida Panthers',
                    'Buffalo Sabres',
                    'Detroit Red Wings']

    #western conference final
    Central =     ['Chicago Blackhawks',
                    'Minnesota Wild',
                    'Nashville Predators',
                    'St. Louis Blues',
                    'Winnipeg Jets',
                    'Dallas Stars',
                    'Colorado Avalanche']

    Pacific = ['San Jose Sharks',
                    'Edmonton Oilers',
                    'Anaheim Ducks',
                    'Calgary Flames',
                    'Los Angeles Kings',
                    'Vancouver Canucks',
                    'Arizona Coyotes']

    def __init__(self):
        self._metropolitan = Teams(Playoffs.Metropolitan, 'Metropolitan')
        self._atlantic = Teams(Playoffs.Atlantic, 'Atlantic')
        self._central = Teams(Playoffs.Central, 'Central')
        self._pacific = Teams(Playoffs.Pacific, 'Pacific')
        self._eastern = [self._metropolitan,self._atlantic]
        self._western = [self._central, self._pacific]
        self._reset = copy.deepcopy((self._eastern, self._western))

    def reset(self):
        self._western = self._reset[0]
        self._eastern = self._reset[1]

    def predict(self):

        def winner(t1, t2):
            denum = t1.rating.mu + t2.rating.mu
            winner = np.random.choice([t1,t2],p=[t1.rating.mu/denum, t2.rating.mu/denum])
            if winner is t1:
                t1.rating, t2.rating = ts.rate_1vs1(t1.rating, t2.rating, drawn=np.random.choice([True, False],p=[0.081,1.0-0.081]))
                return t1
            else:
                t2.rating, t1.rating = ts.rate_1vs1(t2.rating, t1.rating)
                return t2

        Teams.rank(key = 'score')
        winners = []

        def update_progress(progress):
            barLength = 10 # Modify this to change the length of the progress bar
            status = ""
            if isinstance(progress, int):
                progress = float(progress)
            if progress < 0:
                progress = 0
                status = "Halt...\r\n"
            if progress >= 1:
                progress = 1
                status = "Done...\r\n"
            block = int(round(barLength*progress))
            text = "\rPercent: [{0}] {1}%".format( "#"*block + "-"*(barLength-block), int(progress*100))
            sys.stdout.write(text)
            sys.stdout.flush()

        for i in range(100000):
            update_progress((i+1.0)/100000)
            #predict eastern conference
            metropolitan = self._metropolitan.subset(n = 3)
            atlantic = self._atlantic.subset(n = 3)
            wildcards = Teams(self._metropolitan.names(i = 3, n = 1)+self._atlantic.names(i = 3, n = 1)).subset(n = 2)

            #round 1 contestants
            t1, t5 = Teams.order(metropolitan.first, atlantic.first)
            t3, t4 = metropolitan.second, metropolitan.third
            t7, t8 = atlantic.second, atlantic.third
            t6, t2 = Teams.order(wildcards.first, wildcards.second)

            #round 1 winners
            #print('Eastern Conference (Playoff Games)')
            #print('==============================================', end='')
            #print('=============================================')
            #print("Round 1:")
            #print('Game 1: %-25s vs %-25s' % (t1.name, t2.name), end='')
            t1 = winner(t1, t2)
            #print('Winner: ' + t1.name)
            #print('Game 2: %-25s vs %-25s' % (t3.name, t4.name), end='')
            t2 = winner(t3, t4)
            #print('Winner: ' + t2.name)
            #print('Game 3: %-25s vs %-25s' % (t5.name, t6.name), end='')
            t3 = winner(t5, t6)
            #print('Winner: ' + t3.name)
            #print('Game 4: %-25s vs %-25s' % (t7.name, t8.name), end='')
            t4 = winner(t7, t8)
            #print('Winner: ' + t4.name + '\n')

            #round 2 winners
            #print("Round 2:")
            #print('Game 1: %-25s vs %-25s' % (t1.name, t2.name), end='')
            t1 = winner(t1, t2)
            #print('Winner: ' + t1.name)
            #print('Game 2: %-25s vs %-25s' % (t3.name, t4.name), end='')
            t2 = winner(t3, t4)
            #print('Winner: ' + t2.name + '\n')

            #round 3 (eastern conference final)
            #print("Eastern Conference Finals")
            #print('Game 1: %-25s vs %-25s' % (t1.name, t2.name), end='')
            east_t = winner(t1, t2)
            #print('Winner: ' + east_t.name + '\n\n')


            #predict western conference
            central = self._central.subset(n = 3)
            pacific = self._pacific.subset(n = 3)
            wildcards = Teams(self._central.names(i = 3, n = 1)+self._pacific.names(i = 3, n = 1)).subset(n = 2)

            #round 1 contestants
            t1, t5 = Teams.order(central.first, pacific.first)
            t3, t4 = central.second, central.third
            t7, t8 = pacific.second, pacific.third
            t6, t2 = Teams.order(wildcards.first, wildcards.second)


            #round 1 winners
            #print('Western Conference (Playoff Games)')
            #print('==============================================', end='')
            #print('=============================================')
            #print("Round 1:")
            #print('Game 1: %-25s vs %-25s' % (t1.name, t2.name), end='')
            t1 = winner(t1, t2)
            #print('Winner: ' + t1.name)
            #print('Game 2: %-25s vs %-25s' % (t3.name, t4.name), end='')
            t2 = winner(t3, t4)
            #print('Winner: ' + t2.name)
            #print('Game 3: %-25s vs %-25s' % (t5.name, t6.name), end='')
            t3 = winner(t5, t6)
            #print('Winner: ' + t3.name)
            #print('Game 4: %-25s vs %-25s' % (t7.name, t8.name), end='')
            t4 = winner(t7, t8)
            #print('Winner: ' + t4.name + '\n')

            #round 2 winners
            #print("Round 2:")
            #print('Game 1: %-25s vs %-25s' % (t1.name, t2.name), end='')
            t1 = winner(t1, t2)
            #print('Winner: ' + t1.name)
            #print('Game 2: %-25s vs %-25s' % (t3.name, t4.name), end='')
            t2 = winner(t3, t4)
            #print('Winner: ' + t2.name + '\n')

            #round 3 (western conference final)
            #print("Western Conference Finals")
            #print('Game 1: %-25s vs %-25s' % (t1.name, t2.name), end='')
            west_t = winner(t1, t2)
            #print('Winner: ' + west_t.name + '\n\n')

            #stanley cup final match!!
            stanley_cup = winner(west_t, east_t)
            winners.append(stanley_cup.name)
            #print(stanley_cup.name + ' will win the Stanley Cup')
        unique_teams = []
        sorted_teams = []
        for winner in winners:
            if winner not in unique_teams:
                unique_teams.append(winner)
        for team in unique_teams:
            sorted_teams.append((team, winners.count(team)))
        sorted_teams.sort(key=lambda x: x[1], reverse = True)
        for team in sorted_teams:
            print(team)


    def out(self):
        print('==============================================', end='')
        print('=============================================\n')
        print('Eastern Conference (Teams)')
        print('----------------------------------------------', end='')
        print('---------------------------------------------')
        for div in self._eastern:
            div.out()
        print('==============================================', end='')
        print('=============================================\n')
        print('Western Conference (Teams)')
        print('----------------------------------------------', end='')
        print('---------------------------------------------')
        for div in self._western:
            div.out()
        print('==============================================', end='')
        print('=============================================\n')


# END OF CLASS DEFINITIONS

#setup
d1 = date(2016, 10, 12)
d2 = date.today()
delta = d2 - d1
games = 0

#download game data from hockey-reference.com
if not os.path.isfile('data.csv'):
    with open('data.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['date', 'winner', 'win_score', 'loser', 'lose_score', 'extra_time'])
        for i in range(delta.days+1):
            day = d1 + timedelta(days=i)
            print("Getting games for {}".format(day))
            url = "http://www.hockey-reference.com/boxscores/?month={}&day={}&year={}".format(day.month,day.day,day.year)
            html_doc = urlopen(url)
            soup = BeautifulSoup(html_doc, 'html.parser') #print(soup.prettify())
            try:
                for div in soup.find('div', class_ = "game_summaries").find_all('table', class_ = "teams"):
                    games = games + 1
                    winner, score_1 = div.find('tr', class_ = "winner").find_all('td')[:-1]
                    loser, score_2 = div.find('tr', class_ = "loser").find_all('td')[:-1]
                    tag = div.find_all('tr')[-1].find_all('td')[-1]
                    ot = str(tag.string).strip()
                    if ot != 'OT' and ot != 'SO':
                        ot = 'n/a'
                    row = [day, winner.string, score_1.string, loser.string, score_2.string, ot]
                    print(row)
                    writer.writerow(row)
            except e:
                print(e)

#import trueskill and set it up
import trueskill as ts
ts.setup(backend='scipy')
ts.setup(draw_probability=0.081)

#extract teams and outcome of every game
games = []
with open('data.csv', 'r', newline='') as csvfile:
    data = csv.reader(csvfile)
    next(data, None)  # skip the headers
    for row in data:
        date, winner, w_score, loser, l_score, ot = row
        games.append(Game(date, winner, w_score, loser, l_score, ot))

Teams.setup(games)
playoffs = Playoffs()
playoffs.predict()
