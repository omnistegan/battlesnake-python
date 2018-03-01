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
        self.snake_id = None
        self.is_food = False
        self.coord = (row, column)
        self.symbol = {'snakehead': 's', 'snakenemy': 'e', 
                       'snakebody': 'b', 'snaketail': 't', 
                       'food': 'f', 'cell': '_'}
    
    def to_symbol(self):
        if self.is_snakehead == True:
            return(self.symbol['snakehead'])
        elif self.is_snakenemy == True:
            return(self.symbol['snakenemy'])
        elif self.is_food == True:
            return(self.symbol['food'])
        elif self.is_snakebody == True:
            return(self.symbol['snakebody'])
        elif self.is_snaketail == True:
            return(self.symbol['snaketail'])
        else:
            return(self.symbol['cell'])


class Grid:
    def __init__(self, prepend):
        self.coord = [[Cell(row, col) 
                       for col in range(prepend['width'])] 
                       for row in range(prepend['height'])]

    def print(self):
        for row in self.coord:
            for cell in row:
                print(cell.to_symbol(), end=" ")
            print("")

    def place(self, instance, obj): # maybe break into 3 separate functions?
        if obj == 'food':
            for i in range(len(instance)):
                self.coord[instance[i].coord[0]][instance[i].coord[1]].is_food = True
        elif obj == 'enemy':
            for i in range(len(instance)):
                self.coord[instance[i].head[0]][instance[i].head[1]].is_snakenemy = True
                self.coord[instance[i].head[0]][instance[i].head[1]].snake_id = instance[i].id
                self.coord[instance[i].tail[0]][instance[i].tail[1]].is_snaketail = True
                self.coord[instance[i].tail[0]][instance[i].tail[1]].snake_id = instance[i].id
                for j in range(len(instance[i].body)):
                    self.coord[instance[i].body[j][0]][instance[i].body[j][1]].is_snakebody = True
                    self.coord[instance[i].body[j][0]][instance[i].body[j][1]].snake_id = instance[i].id
        elif obj == 'me':
            self.coord[instance.head[0]][instance.head[1]].is_snakehead = True
            self.coord[instance.head[0]][instance.head[1]].snake_id = instance.id
            self.coord[instance.tail[0]][instance.tail[1]].is_snaketail = True    
            self.coord[instance.tail[0]][instance.tail[1]].snake_id = instance.id
            for j in range(len(instance.body)):
                self.coord[instance.body[j][0]][instance.body[j][1]].is_snakebody = True
                self.coord[instance.body[j][0]][instance.body[j][1]].snake_id = instance.id
                 

class Food:
    def __init__(self, prepend):
        self.coord = [prepend['y'], prepend['x']]

    def order(nourriture, cls):
        foods = [(nourriture[i], distance(cls, nourriture[i].coord))
                 for i in range(len(nourriture))]
        foods_ordered = sorted(foods, key = lambda foods: foods[1])
        foods_reordered = [item[0] for item in foods_ordered]
        return(foods_reordered)

class Enemy:
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
        self.dist_closestfood = distance(self, self.foods_ordered[0].coord)

        # distance to food
        # distance to me


class Me:
    def __init__(self, prepend, nourriture):
        self.head = [prepend['body']['data'][0]['y'], 
                     prepend['body']['data'][0]['x']]
        self.tail = [prepend['body']['data'][-1]['y'], 
                     prepend['body']['data'][-1]['x']]
        self.body = [[prepend['body']['data'][j]['y'], 
                      prepend['body']['data'][j]['x']] 
                      for j in range(1, len(prepend['body']['data'])-1)]
        self.health = prepend['health']
        self.length = prepend['length']
        self.id = prepend['id']
        self.foods_ordered = Food.order(nourriture, self)
        self.dist_closestfood = distance(self, self.foods_ordered[0].coord)


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

    for key in directions:
        if (0 <= directions[key][0] < prepend['height'] 
                and 0 <= directions[key][1] < prepend['width'] 
                and agrid.coord[directions[key][0]][directions[key][1]].\
                    is_snakebody == False 
                and agrid.coord[directions[key][0]][directions[key][1]].\
                    is_snakenemy == False): 
            if agrid.coord[directions[key][0]][directions[key][1]].\
                        is_snaketail == True:
                if agrid.coord[directions[key][0]][directions[key][1]].\
                            snake_id != moi.id:
                    target_snake = [target for target in enemy 
                                    if target.id == agrid.coord\
                                            [directions[key][0]][directions[key][1]].snake_id]
                    if distance(target_snake[0], target_snake[0].foods_ordered[0].coord) > 1:
                        space.append(key)
                elif agrid.coord[directions[key][0]][directions[key][1]].snake_id == moi.id: 
                    # Only valid when goal is food
                    if distance(moi, moi.foods_ordered[0].coord) > 1:
                        space.append(key)
            else:
                space.append(key)

    return(space)
    

def path(frm, to, agrid):
    dy = to[0] - frm.head[0]
    dx = to[1] - frm.head[1]
    possible = []

    if dy > 0:
        possible.append('down')
    elif dy < 0:
        possible.append('up')

    if dx > 0:
        possible.append('right')
    elif dx < 0:
        possible.append('left')

    return(possible)


###############################################################################


@bottle.post('/move')
def move():
    # Initialise board and stuff on board
    data = bottle.request.json

    grid = Grid(data)

    foods = [Food(data['food']['data'][i]) 
             for i in range(len(data['food']['data']))]

    me = Me(data['you'], foods) 

    enemies = [Enemy(data['snakes']['data'][i], foods) 
               for i in range(len(data['snakes']['data'])) 
               if data['snakes']['data'][i]['id'] != me.id]

    # Grid for log purposes
    grid.place(foods, 'food')
    grid.place(enemies, 'enemy')
    grid.place(me, 'me')
    grid.print()
    
    # Route setter
    safety = safe(grid, me, enemies, data)
    route = path(me, me.foods_ordered[0].coord, grid)

    for item in safety:
        if item in route:
            output = item
            break
        else:
            output = safety[randint(0, len(safety)-1)] #returns a random safe output
    
    # Info for current turn, for log purposes
    print("Turn: %s" % (data['turn']))
    print('route: %s' % (route))
    print('safety: %s' % (safety))
    print('output: %s' % (output))

    return {
        'move': output,
        'taunt': 'python!'
    }



# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()
if __name__ == '__main__':
    bottle.run(application, host=os.getenv('IP', '0.0.0.0'), port=os.getenv('PORT', '8080'))
