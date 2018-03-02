import bottle
import os
from random import randint

@bottle.route('/static/<path:path>')
def static(path):
    return bottle.static_file(path, root='static/')

@bottle.post('/start')
def start():
    data = bottle.request.json
    game_id = data['game_id']
    print('game id: %s' % (game_id)) # For log purposes, to indicate which game log is showing.

    head_url = '%s://%s/static/head.png' % (
        bottle.request.urlparts.scheme,
        bottle.request.urlparts.netloc
    )

    return {
        'color': '#00FF00',
        'taunt': 'hissss...sss',
        'head_url': head_url,
        'name': 'our-snake',
        'head_type': 'pixel',
        'tail_type': 'pixel',
    }


################################################################################


class Cell:
    def __init__(self, row, column):
        self.is_snakehead = False
        self.is_snakenemy = False # head of enemy snake(s)
        self.is_snakebody = False
        self.is_snaketail = False
        self.safe = True
        self.snake_id = None
        self.is_food = False
        self.coord = (row, column)
        self.symbol = {'snakehead': 's', 'snakenemy': 'e', 
                       'snakebody': 'b', 'snaketail': 't', 
                       'food': 'f', 'cell': '_',
                       'danger': '!'}
    
    def to_symbol(self):
        if self.is_snakehead == True:
            return(self.symbol['snakehead'])
        elif self.is_snakenemy == True:
            return(self.symbol['snakenemy'])
        elif self.is_snakebody == True:
            return(self.symbol['snakebody'])
        elif self.is_snaketail == True:
            return(self.symbol['snaketail'])
        elif self.safe == False:
            return(self.symbol['danger'])
        elif self.is_food == True:
            return(self.symbol['food'])
        else:
            return(self.symbol['cell'])


class Grid:
    def __init__(self, prepend):
        self.height = prepend['height']
        self.width = prepend['width']
        self.coord = [[Cell(row, col) 
                       for col in range(self.width)] 
                       for row in range(self.height)]

    def print(self):
        for row in self.coord:
            for cell in row:
                print(cell.to_symbol(), end=" ")
            print("")

    def food_place(self, nourriture): 
        for i in range(len(nourriture)):
            self.coord[nourriture[i].coord[0]][nourriture[i].coord[1]].is_food = True

    def enemy_place(self, enemy):
        self.coord[enemy.head[0]][enemy.head[1]].is_snakenemy = True
        self.coord[enemy.head[0]][enemy.head[1]].safe = False
        self.coord[enemy.head[0]][enemy.head[1]].snake_id = enemy.id

        self.coord[enemy.tail[0]][enemy.tail[1]].is_snaketail = True
        self.coord[enemy.tail[0]][enemy.tail[1]].snake_id = enemy.id

        for j in range(len(enemy.body)):
            self.coord[enemy.body[j][0]][enemy.body[j][1]].is_snakebody = True
            self.coord[enemy.body[j][0]][enemy.body[j][1]].safe = False
            self.coord[enemy.body[j][0]][enemy.body[j][1]].snake_id = enemy.id
            
        if enemy.longer_than_me == True:
            for i in range(-1,2):
                if 0 <= enemy.head[0]+i < self.height:
                    self.coord[enemy.head[0]+i][enemy.head[1]].safe = False
                if 0 <= enemy.head[1]+i < self.width:
                    self.coord[enemy.head[0]][enemy.head[1]+i].safe = False

        if enemy.dist_closest_food == 1:
            self.coord[enemy.tail[0]][enemy.tail[1]].safe = False

    def me_place(self, moi):
            self.coord[moi.head[0]][moi.head[1]].is_snakehead = True
            self.coord[moi.head[0]][moi.head[1]].snake_id = moi.id

            self.coord[moi.tail[0]][moi.tail[1]].is_snaketail = True    
            self.coord[moi.tail[0]][moi.tail[1]].snake_id = moi.id

            for j in range(len(moi.body)):
                self.coord[moi.body[j][0]][moi.body[j][1]].is_snakebody = True
                self.coord[moi.body[j][0]][moi.body[j][1]].safe = False
                self.coord[moi.body[j][0]][moi.body[j][1]].snake_id = moi.id

            if moi.dist_closest_food == 1:
                self.coord[moi.tail[0]][moi.tail[1]].safe = False
                 

class Food:
    def __init__(self, prepend):
        self.coord = [prepend['y'], prepend['x']]

    def order(nourriture, cls):
        fods = [(nourriture[i], distance(cls, nourriture[i].coord))
                 for i in range(len(nourriture))]
        foods_ordered = sorted(fods, key = lambda fods: fods[1])
        foods_reordered = [item[0] for item in foods_ordered]
        return(foods_reordered)

class Snake:
    def __init__(self, prepend, nourriture):
        self.head = [prepend['body']['data'][0]['y'],
                     prepend['body']['data'][0]['x']]
        self.tail = [prepend['body']['data'][-1]['y'], 
                     prepend['body']['data'][-1]['x']]
        self.body = [[prepend['body']['data'][j]['y'],
                      prepend['body']['data'][j]['x']] 
                      for j in range(1, len(prepend['body']['data'])-1)]
        self.length = prepend['length']
        self.id = prepend['id']
        self.foods_ordered = Food.order(nourriture, self)
        self.dist_closest_food = distance(self, self.foods_ordered[0].coord)

    def target_tail(enemoir, moi, agrid):
        enemy_unordered = [(enemoir[i], distance(moi, enemoir[i].tail))
                        for i in range(len(enemoir))]
        enemy_ordered = sorted(enemy_unordered, key = lambda enemy_unordered:\
                enemy_unordered[1])
        enemy = [item[0] for item in enemy_unordered]
        target = enemy[0]
        
        if target.length > 3: 
            if target.tail == target.body[-1]: # Checks if tail is same as last body segment, then look at second last body segment instead
                if target.tail[0] == target.body[-2][0]:
                    if target.tail[1] < target.body[-2][1]:
                        if target.tail[1]-2 > 0:
                            output = [target.tail[0], target.tail[1]-2]
                        elif target.tail[1]-2 > 0:
                            output = [target.tail[0], target.tail[1]-2]
                        output = target.tail
                    elif target.tail[1]+2 < agrid.width:
                        output = [target.tail[0], target.tail[1]+2]
                    elif target.tail[1]+1 < agrid.width:
                        output = [target.tail[0], target.tail[1]+1]
                    else:
                        output = target.tail

                elif target.tail[1] == target.body[-2][1]:
                    if target.tail[0] < target.body[0]:
                        if target.tail[0]-2 > 0:
                            output = [target.tail[0]-2, target.tail[1]]
                        elif target.tail[0]-2 > 0:
                            output = [target.tail[0]-2, target.tail[1]]
                        output = target.tail
                    elif target.tail[0]+2 < agrid.height:
                        output = [target.tail[0]+2, target.tail[1]]
                    elif target.tail[0]+1 < agrid.height:
                        output = [target.tail[0]+1, target.tail[1]]
                    else:
                        output = target.tail

            elif target.tail[0] == target.body[-1][0]:
                if target.tail[1] < target.body[-1][1]:
                    if target.tail[1]-2 > 0:
                        output = [target.tail[0], target.tail[1]-2]
                    elif target.tail[1]-1 > 0:
                        output = [target.tail[0], target.tail[1]-1]
                    else:
                        output = target.tail
                elif target.tail[1]+2 < agrid.width:
                    output = [target.tail[0], target.tail[1]+2]
                elif target.tail[1]+1 < agrid.width:
                    output = [target.tail[0], target.tail[1]+1]
                else:
                    output = target.tail

            elif target.tail[1] == target.body[-1][1]:
                if target.tail[0] < target.body[-1][0]:
                    if target.tail[0]-2 > 0:
                        output = [target.tail[0]-2, target.tail[1]]
                    elif target.tail[0]-1 > 0:
                        output = [target.tail[0]-1, target.tail[1]]
                    else:
                        output = target.tail
                elif target.tail[0]+2 < agrid.height:
                    output = [target.tail[0]+2, target.tail[1]]
                elif target.tail[0]+1 < agrid.height:
                    output = [target.tail[0]+1, target.tail[1]]
                else:
                    output = target.tail

        return(output)

class Enemy(Snake):
    def __init__(self, prepend, moi, nourriture):
        super().__init__(prepend, nourriture)
        self.longer_than_me = self.length >= moi.length

        # distance to food
        # distance to me

class Me(Snake):
    def __init__(self, prepend, nourriture):
        super().__init__(prepend, nourriture)
        self.health = prepend['health']


################################################################################


def distance(frm, to):
    dy = abs(to[0] - frm.head[0])
    dx = abs(to[1] - frm.head[1])
    return(sum([dy, dx]))
    

def safe(agrid, moi, enemy, prepend):
    directions = {
            'up': [moi.head[0]-1, moi.head[1]],
            'down': [moi.head[0]+1, moi.head[1]],
            'left': [moi.head[0], moi.head[1]-1],
            'right': [moi.head[0], moi.head[1]+1],
            } 

    space = []
    backup_space = []

    for key in directions:
        if (0 <= directions[key][0] < prepend['height'] 
                and 0 <= directions[key][1] < prepend['width'] 
                and agrid.coord[directions[key][0]][directions[key][1]].\
                    safe == True): 
            space.append(key)
    
    for key in directions:
        if (0 <= directions[key][0] < prepend['height'] 
                and 0 <= directions[key][1] < prepend['width'] 
                and agrid.coord[directions[key][0]][directions[key][1]].\
                    is_snakenemy == False
                and agrid.coord[directions[key][0]][directions[key][1]].\
                    is_snakebody == False
                and agrid.coord[directions[key][0]][directions[key][1]].\
                    is_food == False):
            if agrid.coord[directions[key][0]][directions[key][1]].\
                        is_snaketail == True:
                if agrid.coord[directions[key][0]][directions[key][1]].\
                        snake_id != moi.id:
                    target_snake = [target for target in enemy
                                    if target.id == agrid.coord\
                                            [directions[key][0]]\
                                            [directions[key][1]].snake_id]
                    if target_snake[0].dist_closest_food > 1:
                        backup_space.append(key)
                elif agrid.coord[directions[key][0]][directions[key][1]].\
                        snake_id == moi.id:
                    if moi.dist_closest_food > 1:
                        backup_space.append(key)
            else:
                backup_space.append(key)

    return(space, backup_space)
    

def path(frm, to, agrid):
    possible = []

    if to[0]>frm.head[0]:
        possible.append('down')
    elif to[0]<frm.head[0]:
        possible.append('up')

    if to[1]>frm.head[1]:
        possible.append('right')
    elif to[1]<frm.head[1]:
        possible.append('left')

    return(possible)


def goal_set(moi, enemoir, agrid):
    if moi.health <= 30:
        output = moi.foods_ordered[0].coord
    else:
        output = Snake.target_tail(enemoir, moi, agrid)
    return(output)


###############################################################################


@bottle.post('/move')
def move():
    # Initialise board and stuff on board
    data = bottle.request.json

    grid = Grid(data)

    foods = [Food(data['food']['data'][i]) 
             for i in range(len(data['food']['data']))]

    me = Me(data['you'], foods) 

    enemies = [Enemy(data['snakes']['data'][i], me, foods) 
               for i in range(len(data['snakes']['data'])) 
               if data['snakes']['data'][i]['id'] != me.id]

    # Grid for log purposes
    grid.food_place(foods)
    for enemoir in enemies: grid.enemy_place(enemoir)
    grid.me_place(me)
    grid.print()
    
    # Route setter
    safety, backup_safety = safe(grid, me, enemies, data)
    goal = goal_set(me, enemies, grid)
    route = path(me, goal, grid)

    if safety:
        for item in safety:
            if item in route:
                output = item
                break
            else:
                output = safety[randint(0, len(safety)-1)] #returns a random safe output
    else:
        output = backup_safety[randint(0, len(backup_safety)-1)]

    target_practice = Snake.target_tail(enemies, me, grid)
    
    # Info for current turn, for log purposes
    print("Turn: %s" % (data['turn']))
    print('route: %s' % (route))
    print('safety: %s' % (safety))
    print('backup_safety: %s' % (backup_safety))
    print('target tail is: %s' % target_practice)
    print('goal is: %s' % goal)
    print('output: %s' % (output))


    return {
        'move': output,
        'taunt': 'python!'
    }



# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()
if __name__ == '__main__':
    bottle.run(application, host=os.getenv('IP', '0.0.0.0'), port=os.getenv('PORT', '8080'))
