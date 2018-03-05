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
        'taunt': 'A dog. Slitheratively speaking.',
        'head_url': head_url,
        'name': 'Snakosawrus-rex',
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
        #self.coord[moi.head[0]][moi.head[1]].safe = False
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
        log = "food"
    else:
        output = target_tail(enemoir, moi, agrid)
        log = "tail"
    return(output, log)


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
        if (0 <= directions[key][0] < agrid.height
                and 0 <= directions[key][1] < agrid.width
                and agrid.coord[directions[key][0]][directions[key][1]].\
                    safe == True):
            space.append(key)

    for key in directions:
        if (0 <= directions[key][0] < agrid.height
                and 0 <= directions[key][1] < agrid.width
                and agrid.coord[directions[key][0]][directions[key][1]].\
                    is_snakenemy == False
                and agrid.coord[directions[key][0]][directions[key][1]].\
                    is_snakebody == False):
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
            else:
                backup_space.append(key)

    return(space, backup_space)

def target_tail(enemoir, moi, agrid):
        enemy_unordered = [(enemoir[i], distance(moi, enemoir[i].tail))
                        for i in range(len(enemoir))]
        enemy_ordered = sorted(enemy_unordered, key = lambda enemy_unordered:\
                enemy_unordered[1])
        enemy = [item[0] for item in enemy_unordered]
        target = enemy[0]

        output = [target.tail]

        if target.length > 3:
            if target.tail == target.body[-1]: # Checks if tail is same as last body segment, then look at second last body segment instead
                segment = -2
            else:
                segment = -1

            if target.tail[0] == target.body[segment][0]:
                if target.tail[1] < target.body[segment][1]:
                    for i in range(-1, -3, -1):
                        if (target.tail[1]+i >= 0
                            and agrid.coord[target.tail[0]][target.tail[1]+i].\
                                    safe == True):
                            output.append([target.tail[0], target.tail[1]+i])

                elif target.tail[1] > target.body[segment][1]:
                    for i in range(-1, -3, -1):
                        if (target.tail[1]-i < agrid.width
                            and agrid.coord[target.tail[0]][target.tail[1]-i].\
                                    safe == True):
                            output.append([target.tail[0], target.tail[1]-i])

            elif target.tail[1] == target.body[segment][1]:
                if target.tail[0] < target.body[segment][0]:
                    for i in range(-1, -3, -1):
                        if (target.tail[0]+i >= 0
                            and agrid.coord[target.tail[0]+i][target.tail[1]].\
                                    safe == True):
                            output.append([target.tail[0]+i, target.tail[1]])

                elif target.tail[0] > target.body[segment][0]:
                    for i in range(-1, -3, -1):
                        if (target.tail[0]-i < agrid.height
                            and agrid.coord[target.tail[0]-i][target.tail[1]].\
                                    safe == True):
                            output.append([target.tail[0]-i, target.tail[1]])

        return(output[-1])


def check(direction, y, x, agrid):
    change = {'up': [-1, 0],
              'down': [1, 0],
              'left': [0, -1],
              'right': [0, 1]}

    y += change[direction][0]
    x += change[direction][1]

    count = 0
    while(0 <= y < agrid.height and 0 <= x < agrid.width
            and agrid.coord[y][x].is_snakenemy == False
            and agrid.coord[y][x].is_snakebody == False):
        count += 1
        y += change[direction][0]
        x += change[direction][1]

    return(count)


def floodfill(key, moi, agrid):
    y = moi.head[0]
    x = moi.head[1]

    direction_parameter = {'vertical': ['left', 'right'],
                           'horizontal': ['up', 'down']}
    parameter = {'up': -1, 'down': 1,
                 'left': -1, 'right': 1}

    sum = 0
    
    if key == 'up' or key == 'down':
        size = check(key, y, x, agrid)
        sum += size
        for dir in direction_parameter['vertical']:
            for i in range(1, size+1):
                sum += check(dir, y+(i*parameter[key]), x, agrid)
     
    if key == 'left' or key == 'right':
        size = check(key, y, x, agrid)
        sum += size
        for dir in direction_parameter['horizontal']:
            for i in range(1, size+1):
                sum += check(dir, y, x+(i*parameter[key]), agrid)
            
    return(sum)


def floodfill_reorder(space, moi, agrid):
    espace = [(space[i], floodfill(space[i], moi, agrid)) for i in
              range(len(space))]
    espace_ordered = sorted(espace, key = lambda espace: espace[1], reverse=True)
    #print(espace)
    espace_reordered = [item[0] for item in espace_ordered]

    return(espace_reordered)


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
    flooding_safe = floodfill_reorder(safety, me, grid)
    flooding_backup = floodfill_reorder(backup_safety, me, grid)
    goal, output_log = goal_set(me, enemies, grid)
    route = path(me, goal, grid)
    flooding_route = floodfill_reorder(route, me, grid)

    if flooding_safe: #If safety is not empty
        for item in flooding_safe:
            if output_log == 'food':
                if item in flooding_route:
                    output = item
                    break
            elif output_log == 'tail':
                output = flooding_safe[0]
    else:
        output = flooding_backup[0]

    target_practice = target_tail(enemies, me, grid)


    # Info for current turn, for log purposes
    print('Floodfill Up: %s' % (floodfill('up', me, grid)))
    print('Floodfill Down: %s' % (floodfill('down', me, grid)))
    print('Floodfill Left: %s' % (floodfill('left', me, grid)))
    print('Floodfill Right: %s' % (floodfill('right', me, grid)))
    print('Health: %s' % (me.health))
    print('Currently targeting: %s' % output_log)
    print("Turn: %s" % (data['turn']))
    print('Route: %s' % (route))
    print('Flood route: %s' % (flooding_route))
    print('Safety: %s' % (safety))
    print('Flood Safe: %s' % (flooding_safe))
    print('Backup: %s' % (backup_safety))
    print('Flood backup: %s' % (flooding_backup))
    print('Target tail is: %s' % (target_practice))
    print('Target food is: %s' % (me.foods_ordered[0].coord))
    print('Goal is: %s' % (goal))
    print('output: %s' % (output))

    return {
        'move': output,
        'taunt': 'A dog. Slitheratively speaking.'
    }



# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()
if __name__ == '__main__':
    bottle.run(application, host=os.getenv('IP', '0.0.0.0'), port=os.getenv('PORT', '8080'))
