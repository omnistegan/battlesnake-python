import bottle
import os

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
        self.is_food = False
        self.coord = (row, column)
        self.symbol = {'snakehead': 's', 'snakenemy': 'e', 'snakebody': 'b', 'snaketail': 't', 'food': 'f', 'cell': '_'}
    
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
        self.coord = [[Cell(row, col) for col in range(prepend['width'])] for row in range(prepend['height'])]

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
                self.coord[instance[i].tail[0]][instance[i].tail[1]].is_snaketail = True
                for j in range(len(instance[i].body)):
                    self.coord[instance[i].body[j][0]][instance[i].body[j][1]].is_snakebody = True
        elif obj == 'me':
            self.coord[instance.head[0]][instance.head[1]].is_snakehead = True
            self.coord[instance.tail[0]][instance.tail[1]].is_snaketail = True    
            for j in range(len(instance.body)):
                self.coord[instance.body[j][0]][instance.body[j][1]].is_snakebody = True
                 

class Food:
    def __init__(self, prepend):
        self.coord = [prepend['y'], prepend['x']]


class Enemy:
    def __init__(self, prepend, nourriture):
        self.head = [prepend['body']['data'][0]['y'], prepend['body']['data'][0]['x']]
        self.tail = [prepend['body']['data'][-1]['y'], prepend['body']['data'][-1]['x']]
        self.body = [[prepend['body']['data'][j]['y'], prepend['body']['data'][j]['x']] for j in range(1, len(prepend['body']['data'])-1)]
        self.length = prepend['length']
        self.id = prepend['id']
        self.foods = [
                (nourriture[i], distance(self, nourriture[i]))
                for i in range(len(nourriture))
                ]
        self.foods_ordered = sorted(self.foods, key = lambda foods: foods[1])

        # distance to food
        # distance to me


class Me:
    def __init__(self, prepend, nourriture):
        self.head = [prepend['body']['data'][0]['y'], prepend['body']['data'][0]['x']]
        self.tail = [prepend['body']['data'][-1]['y'], prepend['body']['data'][-1]['x']]
        self.body = [[prepend['body']['data'][j]['y'], prepend['body']['data'][j]['x']] for j in range(1, len(prepend['body']['data'])-1)]
        self.health = prepend['health']
        self.length = prepend['length']
        self.id = prepend['id']
        self.foods = [
                (nourriture[i], distance(self, nourriture[i]))
                for i in range(len(nourriture))
                ]
        self.foods_ordered = sorted(self.foods, key = lambda foods: foods[1])
        #self.distance_food = distance(self, )


################################################################################


def distance(frm, to):
    dy = abs(to.coord[0] - frm.head[0])
    dx = abs(to.coord[1] - frm.head[1])
    return(sum([dy, dx]))
    

def safe(agrid, snake, prepend):
    directions = {
            'up': [snake.head[0]-1, snake.head[1]],
            'down': [snake.head[0]+1, snake.head[1]],
            'left': [snake.head[0], snake.head[1]-1],
            'right': [snake.head[0], snake.head[1]+1],
            } 

    space = [key for key in directions
            if 0 <= directions[key][0] < prepend['height']
            and 0 <= directions[key][1] < prepend['width']
            and agrid.coord[directions[key][0]][directions[key][1]].is_snakebody == False 
            and agrid.coord[directions[key][0]][directions[key][1]].is_snakenemy == False # Update this condition - set to two block buffer
            ]

    return(space)
    

def path(frm, to, agrid):
    dy = to.coord[0] - frm.head[0]
    dx = to.coord[1] - frm.head[1]
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

    foods = [Food(data['food']['data'][i]) for i in range(len(data['food']['data']))]
    #foods.sort(key = lambda food: food.distance)

    me = Me(data['you'], foods) 

    enemy = [Enemy(data['snakes']['data'][i], foods) for i in range(len(data['snakes']['data'])) if data['snakes']['data'][i]['id'] != me.id]

    # Grid for log purposes
    grid.place(foods, 'food')
    grid.place(enemy, 'enemy')
    grid.place(me, 'me')
    grid.print()
    
    # Route setter
    safety = safe(grid, me, data)
    route = path(me, foods[0], grid)

    for item in safety:
        if item in route:
            output = item
            break
        else:
            output = safety[-1]
    
    # Info for current turn, for log purposes
    print("Turn: %s" % (data['turn']))
    print('route: %s' % (route))
    print('safety: %s' % (safety))
    print('output: %s' % (output))
    print(enemy[0].foods_ordered[0], enemy[1].foods_ordered[0])

    return {
        'move': output,
        'taunt': 'python!'
    }



# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()
if __name__ == '__main__':
    bottle.run(application, host=os.getenv('IP', '0.0.0.0'), port=os.getenv('PORT', '8080'))
