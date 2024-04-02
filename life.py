from typing import List, Tuple, Set
import numpy as np
import time
import random
import sdl2
import sdl2.ext
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import cProfile
import threading
import ctypes
from PIL import Image

class Cell:
    """
    Tipo célula. Contiene la información base de una célula viva.

    La información base es la posición bidimensional de esa célula. Se determina con las variables X e Y.
    """
    def __init__(self, X: int, Y: int) -> None:
        self.X = X
        self.Y = Y
    
    def __str__(self) -> str:
        return f'({self.X},{self.Y})'
    
    def __eq__(self, other) -> bool:
        """
        Dos objetos Cell son iguales si sus componentes X e Y son iguales.
        """
        if not isinstance(other, Cell):
            return False
        return self.X == other.X and self.Y == other.Y
    
    def __hash__(self) -> int:
        """
        Al igual que `eq`, el hashcode depende de las componentes X e Y.
        """
        return hash((self.X, self.Y))

class Grid:
    """
    Tipo rejilla. Almacena un conjunto de células (las que viven) y sus posiciones.
    """    
    def __init__(self, initial_state: Set[Cell]) -> None:
        
        self.live = initial_state.copy()
        self.new_live = self.live.copy()

    def __str__(self) -> str:
        cells_str = ', '.join(str(cell) for cell in self.live)
        return f'Grid: {id(self)}. {len(self.live)} Cells (X,Y): {{{cells_str}}}.'
    
    def copy(self):
        return Grid(self.live.copy())
    
    def count_neighbors(self, cell: Cell) -> int:
        neighbors = 0

        for i in range(cell.X -1, cell.X + 2):
            for j in range(cell.Y -1, cell.Y + 2):
                if Cell(i,j) in self.live:
                    neighbors += 1

        return neighbors
    
    def cell_state_update(self, cell: Cell) -> None:
        if cell in self.live:
            self.live.discard(cell)
        else:
            self.live.add(cell)
    
    def update_cell(self, cell) -> None:
        #start = time.time()
        """
        WORK IN PROGRESS
        """
        neighbors_count = 0

        for i in range(cell.X -1, cell.X + 2):
            for j in range(cell.Y -1, cell.Y + 2):
                if not (i == cell.X and j == cell.Y):
                    """
                    Recorremos todos los vecinos de cada célula viva (a partir de ahora llamados vecinos no triviales).
                    El caso i == cell.X and j == cell.Y corresponde a la propia célula (no es un vecino).
                    """
                    new_cell = Cell(i,j)
                    """
                    Creamos una nueva célula que potencialmente puede vivir.
                    """
                    if new_cell not in self.live:
                        """
                        Nos aseguramos de que esa célula no exista ya.
                        Si la célula ya existe la recorreremos al recorrer `self.live` y por tanto actuar sobre ella aquí
                            supondría problemas de incoherencia.                            
                        """
                        new_cell_neighbors = self.count_neighbors(new_cell)
                        if new_cell_neighbors == 3:
                            """
                            Si finalmente esa potencial célula cumple los requisitos de vecindad, será una célula viva el próximo ciclo.
                            """
                            self.new_live.add(new_cell)
                            """
                            TODO:
                            Actualmente exite la posibilidad de que varias células se recalculen más de una vez.
                            En el peor de los casos una célula se puede llegar a calcular 8 veces en lugar de 1.
                            Esto en principio no debería de provocar grandes problemas de rendimiento,
                                en caso de que se observe un rendimiento mediocre, este podría ser un punto a considerar.
                            """
                    else:
                        neighbors_count += 1

        if neighbors_count < 2 or neighbors_count > 3:
            self.new_live.discard(cell)
        #print("Single Cell update time: ",start - time.time())

    def generate_image(self, cell: Cell, image):
        shape = int(image.shape[0])
        fixed_position = shape // 2
        image[fixed_position + cell.X : (fixed_position + cell.X + 1), fixed_position + cell.Y : (fixed_position + cell.Y + 1), :] = 255


    def update_grid(self) -> None:
        #start_moment = time.time()
        self.new_live = self.live.copy()

        def process_cell(cell):
        
            """
            Recorremos solo las células existentes y no todas las casillas.
            """
            
            self.update_cell(cell)            

        for cell in self.live:
            process_cell(cell)
        
        self.live = self.new_live.copy()
        #print("Update time: ", time.time() - start_moment)
        

def generate_random_cells(num_cells : int) -> set:
    random_cells = set()
    for _ in range(num_cells):
        random_cells.add(Cell(random.randint(-100, 100), random.randint(-100, 100)))
    return random_cells
    

class Window:

    fps_counter = 0
    last_mouse_x = 0
    last_mouse_y = 0
    dragging = False
    start_time = time.time()

    def __init__(self, SCREEN_WIDTH, SCREEN_HEIGHT, CELL_SIZE, render_flags, backend):
        self.zoom = 8
        self.view_x = 0
        self.view_y = 0

        self.paused = False

        sdl2.ext.init()
        self.window = sdl2.ext.Window("Game of Life", size=(SCREEN_WIDTH, SCREEN_HEIGHT))
        self.window.show()
        self.renderer = sdl2.ext.Renderer(self.window, flags=render_flags, backend=backend)

        self.texture = self.load_texture('texture.png')
        self.CELL_SIZE = CELL_SIZE
        self.running = True

    def load_texture(self, image_path: str):
        surface = sdl2.ext.load_image(image_path)
        texture = sdl2.ext.Texture(self.renderer, surface)
        sdl2.SDL_FreeSurface(surface)
        return texture
    
    def show_fps(self):
        self.fps_counter += 1
        current_time = time.time()

        if current_time - self.start_time >= 1.0:
            elapsed_time = current_time - self.start_time
            average_fps = self.fps_counter / elapsed_time

            self.window.title = f"FPS: {int(average_fps)}"
            self.fps_counter = 0
            self.start_time = current_time

    def event_handler(self, grid: Grid, event):    
        if event.type == sdl2.SDL_QUIT:
            self.running = False
        elif event.type == sdl2.SDL_MOUSEBUTTONDOWN:
            if event.button.button == sdl2.SDL_BUTTON_RIGHT:
                self.dragging = True
                self.last_mouse_x, self.last_mouse_y = event.button.x, event.button.y
            elif event.button.button == sdl2.SDL_BUTTON_LEFT and self.paused:
                x, y = ctypes.c_int(0), ctypes.c_int(0)
                sdl2.mouse.SDL_GetMouseState(ctypes.byref(x), ctypes.byref(y))
                input_cell = Cell(int((x.value)* (1/self.zoom) + self.view_x), int((y.value) * (1/self.zoom) + self.view_y))
                grid.cell_state_update(input_cell) 
                print(self.view_x, y.value)      
        elif event.type == sdl2.SDL_MOUSEBUTTONUP:
            if event.button.button == sdl2.SDL_BUTTON_RIGHT:
                self.dragging = False
        elif event.type == sdl2.SDL_MOUSEMOTION:
            if self.dragging:
                dx = event.motion.x - self.last_mouse_x
                dy = event.motion.y - self.last_mouse_y
                self.view_x -=  (dx // (self.CELL_SIZE)) * (1/self.zoom)
                self.view_y -=  (dy // (self.CELL_SIZE)) * (1/self.zoom)
                self.last_mouse_x, self.last_mouse_y = event.motion.x, event.motion.y
        elif event.type == sdl2.SDL_MOUSEWHEEL:
            if event.wheel.y > 0:
                self.zoom *= 2
            elif event.wheel.y < 0 and self.zoom> 1:
                self.zoom /= 2
        elif event.type == sdl2.SDL_KEYDOWN:
            if event.key.keysym.sym == sdl2.SDLK_SPACE:
                self.paused = not self.paused

    def draw_window(self, grid: Grid, iteration, generate):
        #start_drawing = time.time()
        self.renderer.clear()
        for event in sdl2.ext.get_events():
            self.event_handler(grid, event)            

        image = np.zeros((500, 500, 3), dtype=np.uint8)

        for cell in grid.live:
            rect = sdl2.SDL_Rect(
                int((cell.X - self.view_x) * self.CELL_SIZE * self.zoom),
                int((cell.Y - self.view_y) * self.CELL_SIZE * self.zoom),
                int(self.CELL_SIZE * self.zoom), int(self.CELL_SIZE * self.zoom))
            self.renderer.copy(self.texture, None, rect)

            
            if generate: 
                grid.generate_image(cell, image)

        if generate:
            img = Image.fromarray(image.transpose(1,0,2))
            img.save(f"./generated/{hash(grid)}_{iteration}.png")
            
        self.renderer.present()

        
        #print(time.time() - start_drawing)

def render_loop(window, grid, generate = False):
    iteration = 0
    while window.running:        
        window.draw_window(grid, iteration, generate)

        if not window.paused:
            grid.update_grid()
        
        window.show_fps()

        iteration = iteration + 1

def configure(random_init = False):
    random_cells = generate_random_cells(0)

    if random_init: random_cells = generate_random_cells(1000000)

    render_flags = (
          sdl2.SDL_RENDERER_ACCELERATED
      )
    
    backend = "direct3d12"

    grid = Grid(random_cells)
    window = Window(1280, 720, 1, render_flags, backend)

    return (window, grid)

def main():
    window, grid = configure(True)
    generate = True
    render_loop(window, grid, generate)

if __name__ == "__main__":
    main()

#TODO: Hay que arreglar un bug que ocurre al desplazarse a la parte negativa de la pantalla
    #   'arriba izquierda'. Este bug provoca que la creación de nuevas células no sea precisa.
    #   Es decir, las coordenadas x e y no se calculan correctamente. (Tendrá que ver con la componente
    #   negativa de dx y dy).