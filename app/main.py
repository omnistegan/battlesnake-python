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
        'taunt': 'A dog. Slitheratively speaking.',
        'head_url': head_url,
        'name': 'Snakosawrus-rex',
        'head_type': 'pixel',
        'tail_type': 'pixel',
    }


################################################################################

PRIORIZE_FOOD_THRESHOLD = 30
SYMBOL_MAP = {
    'snakehead': 's',
    'snakenemy': 'e',
    'snakebody': 'b',
    'snaketail': 't',
    'food': 'f',
    'empty': '_'
}

class Cell:
    def __init__(self, row, column):
        self.state = 'empty'
        self.safe = True
        self.snake_id = None
        self.coord = (row, column)

    def to_symbol(self):
        return(SYMBOL_MAP[self.state])


class Grid:
    def __init__(self, prepend):
        self.height = prepend['height']
        self.width = prepend['width']
        self.grid = [[Cell(row, col)
                       for col in range(self.width)]
                       for row in range(self.height)]

    def neighbors(self, coord):
        y, x = coord
        neighbors = []
        for i in range(-1, 2, 2):
            if 0 <= x+i < self.height:
                neighbors.append((y, x+i))
            if 0 <= y+i < self.width:
                neighbors.append((y+i, x))
        return neighbors

    def safe(self, coord):
        if coord[0] < 0 or coord[1] < 0 or coord[0] >= self.height or coord[1] >= self.width:
            return False
        else:
            return(self.cell_at(coord).safe)

    def safeish(self, coord):
        if coord[0] < 0 or coord[1] < 0 or coord[0] >= self.height or coord[1] >= self.width:
            return False
        elif cell_at(coord).state in ['empty', 'snaketail', 'food']:
            return True
        else:
            return False

    def cell_at(self, coord):
        y, x = coord
        return(self.grid[x][y])

    def set_at(self, coord, state, snake_id=None, safe=True):
        y, x = coord
        self.grid[x][y].state = state
        self.grid[x][y].snake_id = snake_id
        self.grid[x][y].safe = safe

    def print_grid(self):
        for row in self.grid:
            for cell in row:
                print(cell.to_symbol(), end=" ")
            print("")

    def place_food(self, food_list):
        for food in food_list:
            self.set_at(food.coord, 'food')

    def place_enemy(self, enemy):
        self.set_at(enemy.head, 'snakenemy', enemy.id, False)
        for body in enemy.body:
            self.set_at(body, 'snakebody', enemy.id, False)
        self.set_at(enemy.tail, 'snaketail', enemy.id, not enemy.dist_closest_food == 1)

        if enemy.longer_than_me:
            for neighbor in self.neighbors(enemy.head):
                self.set_at(neighbor, 'empty', None, False)

    def place_me(self, me):
        self.set_at(me.head, 'snakehead', me.id, False)
        for body in me.body:
            self.set_at(body, 'snakebody', me.id, False)
        self.set_at(me.tail, 'snaketail', me.id, not me.dist_closest_food == 1)


class Food:
    def __init__(self, prepend):
        self.coord = [prepend['y'], prepend['x']]

class Snake:
    def __init__(self, prepend, food_list):
        self.head = [prepend['body']['data'][0]['y'],
                     prepend['body']['data'][0]['x']]
        self.tail = [prepend['body']['data'][-1]['y'],
                     prepend['body']['data'][-1]['x']]
        self.body = [[prepend['body']['data'][j]['y'],
                      prepend['body']['data'][j]['x']]
                      for j in range(1, len(prepend['body']['data'])-1)]
        self.length = prepend['length']
        self.id = prepend['id']
        self.foods_ordered = ordered_objects(food_list, self.head)
        self.dist_closest_food = distance(self.head, self.foods_ordered[0].coord)

class Enemy(Snake):
    def __init__(self, prepend, me, food_list):
        super().__init__(prepend, food_list)
        self.longer_than_me = self.length >= me.length

class Me(Snake):
    def __init__(self, prepend, food_list):
        super().__init__(prepend, food_list)
        self.health = prepend['health']


class Game:
    def __init__(self, prepend):
        self.grid = Grid(prepend)
        self.foods = [Food(food_prepend)
                      for food_prepend in prepend['food']['data']]
        self.me = Me(prepend['you'], self.foods)
        self.enemies = [Enemy(enemy_prepend, self.me, self.foods)
                        for enemy_prepend in prepend['snakes']['data']
                        if enemy_prepend['id'] != self.me.id]

        self.grid.place_food(self.foods)
        for enemy in self.enemies:
            self.grid.place_enemy(enemy)
        self.grid.place_me(self.me)
        self.grid.print_grid()

    def goal_set(self):
        if self.me.health <= PRIORIZE_FOOD_THRESHOLD:
            output = self.me.foods_ordered[0].coord
            log = "food"
        else:
            output = self.target_tail()
            log = "tail"
        return(output, log)

    def target_tail(self):
        output = []
        target_snake = [sorted(self.enemies, key = lambda enemy: distance(self.me.head, enemy.tail))[0]]
        tail_coord = target_snake.tail
        if self.grid.safe(tail_coord):
            output.append(tail_coord)

        target_dir = find_target_direction(target_snake)

        for i in range(1, 3):
            if target_dir == 'down':
                    coord = (target_coord[0]+i, target_coord[1])
                    if self.grid.safe(coord):
                        output.append(coord)
            elif target_dir == 'up':
                    coord = (target_coord[0]-i, target_coord[1])
                    if self.grid.safe(coord):
                        output.append(coord)
            elif target_dir == 'right':
                    coord = (target_coord[0], target_coord[1]+i)
                    if self.grid.safe(coord):
                        output.append(coord)
            elif target_dir == 'left':
                    coord = (target_coord[0], target_coord[1]-i)
                    if self.grid.safe(coord):
                        output.append(coord)

        return(output)

    def safe_coords(self):
        safe = []
        for coord in self.grid.neighbors(self.me.head):
            if self.grid.safe(coord):
                safe.append(coord)

        if len(safe) == 0:
            for coord in self.grid.neighbors(self.me.head):
                if self.grid.safeish(coord):
                    safe.append(coord)

        return(safe)

    def safe_directions(self):
        safe_directions = []
        safe_coords = self.safe_coords()
        for choice in safe_coords:
            if choice[0] > self.me.head[0]:
                safe_directions.append('down')
            elif choice[0] < self.me.head[0]:
                safe_directions.append('up')
            elif choice[1] > self.me.head[1]:
                safe_directions.append('right')
            elif choice[1] < self.me.head[1]:
                safe_directions.append('left')
        return safe_directions


################################################################################


def find_target_direction(target_snake):
    tail = target_snake.tail
    if target_snake.tail == target_snake.body[-1]:
        body = target_snake.body[-2]
    else:
        body = target_snake.body[-1]

    if body[0] < tail[0]:
        return 'bottom'
    elif body[0] > tail[0]:
        return 'top'
    elif body[1] < tail[1]:
        return 'right'
    elif body[1] > tail[1]:
        return 'left'


def ordered_objects(obj_list, target):
    return(sorted(obj_list, key = lambda obj: distance(obj.coord, target)))


def distance(frm, to):
    dy = abs(to[0] - frm[0])
    dx = abs(to[1] - frm[1])
    return(sum([dy, dx]))


def path(frm, to):
    possibilities = []

    if to[0]>frm[0]:
        possibilities.append('down')
    elif to[0]<frm[0]:
        possibilities.append('up')

    if to[1]>frm[1]:
        possibilities.append('right')
    elif to[1]<frm[1]:
        possibilities.append('left')

    return(possibilities)


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

    game = Game(data)

    # Route setter
    safe_directions = game.safe_directions()

    flooding_safe = floodfill_reorder(safety, me, grid)
    flooding_backup = floodfill_reorder(backup_safety, me, grid)
    goal, output_log = goal_set(me, enemies, grid)
    route = path(me.head, goal, grid)
    flooding_route = floodfill_reorder(route, me, grid)

    output = None
    if flooding_safe: #If safety is not empty
        for item in flooding_safe:
            if output_log == 'food':
                if item in flooding_route:
                    output = item
            elif output_log == 'tail':
                output = flooding_safe[0]
        if output == None:
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
