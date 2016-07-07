from elements import *

from core.color import *

import pygame
from pygame.locals import *
from pygame.sprite import *
import pykinect
from pykinect import nui
from pykinect.nui import JointId, SkeletonTrackingState

import ctypes
import thread

KINECTEVENT = pygame.USEREVENT

video_display = False

kinect = nui.Runtime()
kinect.skeleton_engine.enabled = True

screen_lock = thread.allocate()

if hasattr(ctypes.pythonapi, 'Py_InitModule4'):
   Py_ssize_t = ctypes.c_int
elif hasattr(ctypes.pythonapi, 'Py_InitModule4_64'):
   Py_ssize_t = ctypes.c_int64
else:
   raise TypeError("Cannot determine type of Py_ssize_t")

_PyObject_AsWriteBuffer = ctypes.pythonapi.PyObject_AsWriteBuffer
_PyObject_AsWriteBuffer.restype = ctypes.c_int
_PyObject_AsWriteBuffer.argtypes = [ctypes.py_object,
                                  ctypes.POINTER(ctypes.c_void_p),
                                  ctypes.POINTER(Py_ssize_t)]

def surface_to_array(surface):
   buffer_interface = surface.get_buffer()
   address = ctypes.c_void_p()
   size = Py_ssize_t()
   _PyObject_AsWriteBuffer(buffer_interface,
                          ctypes.byref(address), ctypes.byref(size))
   bytes = (ctypes.c_byte * size.value).from_address(address.value)
   bytes.object = buffer_interface
   return bytes

def draw_skeletons(skeletons):
    for index, data in enumerate(skeletons):
        # draw the Head
        HeadPos = skeleton_to_depth_image(data.SkeletonPositions[JointId.Head], dispInfo.current_w, dispInfo.current_h) 
        draw_skeleton_data(data, index, SPINE, 10)
        pygame.draw.circle(screen, SKELETON_COLORS[index], (int(HeadPos[0]), int(HeadPos[1])), 20, 0)
    
        # drawing the limbs
        draw_skeleton_data(data, index, LEFT_ARM)
        draw_skeleton_data(data, index, RIGHT_ARM)
        draw_skeleton_data(data, index, LEFT_LEG)
        draw_skeleton_data(data, index, RIGHT_LEG)


def depth_frame_ready(frame):
    if video_display:
        return

    with screen_lock:
        address = surface_to_array(screen)
        frame.image.copy_bits(address)
        del address
        if skeletons is not None and draw_skeleton:
            draw_skeletons(skeletons)
        pygame.display.update()    


def video_frame_ready(frame):
    if not video_display:
        return

    with screen_lock:
        address = surface_to_array(screen)
        frame.image.copy_bits(address)
        del address
        if skeletons is not None and draw_skeleton:
            draw_skeletons(skeletons)
        pygame.display.update()

def post_frame(frame):
    try:
        pygame.event.post(pygame.event.Event(KINECTEVENT, skeletons = frame.SkeletonData))
    except:
        pass

# class that does most of the game processing
class Controller(object):
	# set up class variables
	def __init__(self, game):
		self.game = game
		font_location = pygame.font.match_font("stormfazeregular")
		font_size = int(game.screensize[0]/12)
		self.font = pygame.font.Font(font_location, font_size)
		self.color = {}
		self.color['ball'] = GREEN
		self.color['left'] = RED
		self.color['right'] = BLUE
		self.color['line'] = YELLOW
		self.color['text'] = WHITE
		self.paddle_offset = game.screensize[0]*.04
		self.paddle_height = game.screensize[1]*.26
		self.game_middle_x = game.screensize[0]/2
		self.game_middle_y = game.screensize[1]/2
		self.left_score_x = self.game_middle_x - font_size
		self.right_score_x = self.game_middle_x + font_size/3
		self.score_y = 16
		kinect = nui.Runtime()
		kinect.camera.elevation_angle = 8
		kinect.skeleton_engine.enabled = True
		kinect.skeleton_frame_ready += post_frame
		kinect.video_frame_ready += video_frame_ready    
		kinect.video_stream.open(nui.ImageStreamType.Video, 2, 
                                      nui.ImageResolution.Resolution640x480, 
                                      nui.ImageType.Color)
	# method that returns everything to its original position
	def set(self):
		self.ball = Ball(self.game.screen, self.color['ball'], (self.game_middle_x, self.game_middle_y), 14, 4)
		self.ball.draw()
		self.ball.x = 12
		self.ball.y = 0
		self.left = Paddle(self.game.screen, self.color['left'], self.paddle_offset, self.game_middle_y-self.paddle_height/2, self.paddle_offset/2, self.paddle_height, 4)
		self.left.draw()
		self.right = Paddle(self.game.screen, self.color['right'], self.game.screensize[0]-self.paddle_offset*1.5, self.game_middle_y-self.paddle_height/2, self.paddle_offset/2, self.paddle_height, 4)
		self.right.draw()
		self.midline = Line(self.game.screen, self.color['line'], (self.game_middle_x, 0), (self.game_middle_x, self.game.screensize[1]), 4)
		self.midline.draw()
		self.midcircle = Circle(self.game.screen, self.color['line'], (self.game_middle_x, self.game_middle_y), int(self.game.screensize[1]/4), 4)
		self.midcircle.draw()
	# method that sets up the game
	def start(self):
		# draw all objects
		self.set()
		# draw midline and hidden lines around outline of screen
		self.left_score = Text(self.game.screen, self.font, "0", self.color['text'], (self.left_score_x, self.score_y))
		self.left_score.draw()
		self.right_score = Text(self.game.screen, self.font, "0", self.color['text'], (self.right_score_x, self.score_y))
		self.right_score.draw()
		# show those elements
		self.game.render()
		self.players = []
	# method that continues the game
	def go(self):
		# move paddles to kinect locations
		events = pygame.event.get()
		for e in events:
			if e.type == KINECTEVENT:
				for skeleton in e.skeletons:
					right_hand = skeleton.SkeletonPositions[JointId.HandRight]
					if (not right_hand.y==0):
						ypos = (1-right_hand.y) * self.game.screensize[1]
						self.right.move(ypos)
					left_hand = skeleton.SkeletonPositions[JointId.HandLeft]
					if (not left_hand.y==0):
						ypos = (1-left_hand.y) * self.game.screensize[1]
						self.left.move(ypos)
			elif e.type == KEYDOWN:
				if e.key == K_ESCAPE:
					self.game.quit()
		self.midline.draw()
		self.midcircle.draw()
		self.left.change()
		self.right.change()
		self.ball.change()
		balloldx = self.ball.x
		balloldy = self.ball.y
		# check if ball hits the top/bot of screen and bounce off
		if self.ball.pos[1]+self.ball.rad>=self.game.screensize[1] or self.ball.pos[1]-self.ball.rad<=0:
			self.ball.y = -self.ball.y
		# calculate if the ball hits a paddle
		# right paddle
		if self.ball.rect.colliderect(self.right.rect):
			ball = self.ball.pos[1]
			bot = self.right.rect.bottom
			length = bot - self.right.rect.top
			sixth = int(length/5)
			div = [bot, bot-sixth, bot-2*sixth, bot-3*sixth, bot-4*sixth, self.right.rect.top]
			# decide where it is hitting
			if (div[0] >= ball > div[1]):
				self.ball.x = -self.ball.x + 4
				if self.ball.x >= 0:
					self.ball.x = -5
				if self.ball.y > 0:
					self.ball.y -= 4
				else:
					self.ball.y += 4
			elif (div[1] >= ball > div[2]):
				self.ball.x = -self.ball.x - 4
				if self.ball.x >= 0:
					self.ball.x = -8
				if self.ball.y > 0:
					self.ball.y -= 2
				else:
					self.ball.y += 2
			elif (div[2] >= ball > div[3]):
				self.ball.x = -self.ball.x - 10
				if self.ball.x >= 0:
					self.ball.x = -14
			elif (div[3] >= ball > div[4]):
				self.ball.x = -self.ball.x - 4
				if self.ball.x >= 0:
					self.ball.x = -8
				if self.ball.y > 0:
					self.ball.y += 2
				else:
					self.ball.y -= 2
			elif (div[4] > ball > div[5]):
				self.ball.x = -self.ball.x + 4
				if self.ball.x >= 0:
					self.ball.x = -5
				if self.ball.y > 0:
					self.ball.y += 4
				else:
					self.ball.y -= 4
		# left paddle
		if self.ball.rect.colliderect(self.left.rect):
			ball = self.ball.pos[1]
			bot = self.left.rect.bottom
			length = bot - self.left.rect.top
			sixth = int(length/5)
			div = [bot, bot-sixth, bot-2*sixth, bot-3*sixth, bot-4*sixth, self.right.rect.top]
			# decide where it is hitting
			if (div[0] >= ball > div[1]):
				self.ball.x = -self.ball.x - 4
				if self.ball.x >= 0:
					self.ball.x = 5
				if self.ball.y > 0:
					self.ball.y -= 4
				else:
					self.ball.y += 4
			elif (div[1] >= ball > div[2]):
				self.ball.x = -self.ball.x + 4
				if self.ball.x <= 0:
					self.ball.x = 8
				if self.ball.y > 0:
					self.ball.y -= 2
				else:
					self.ball.y += 2
			elif (div[2] >= ball > div[3]):
				self.ball.x = -self.ball.x + 10
			elif (div[3] >= ball > div[4]):
				self.ball.x = -self.ball.x + 4
				if self.ball.x <= 0:
					self.ball.x = 8
				if self.ball.y > 0:
					self.ball.y += 2
				else:
					self.ball.y -= 2
			elif (div[4] > ball > div[5]):
				self.ball.x = -self.ball.x - 4
				if self.ball.x <= 0:
					self.ball.x = 5
				if self.ball.y > 0:
					self.ball.y += 4
				else:
					self.ball.y -= 4
		# make sure that speed does not ever exceed 20 and is never below 5
		if self.ball.x < -20:
			self.ball.x = -20
		elif self.ball.x > 20:
			self.ball.x = 20
		elif abs(self.ball.x) < 8:
			if self.ball.x > 0:
				self.ball.x = 8
			else:
				self.ball.x = -8
		if self.ball.y < -20:
			self.ball.y = -20
		elif self.ball.y > 20:
			self.ball.y = 20
		# store the original score before possibly updating it
		left_score = int(self.left_score.content)
		right_score = int(self.right_score.content)
		# check if the score should be updated
		if self.ball.pos[0]+self.ball.rad<=0:
			right_score+=1
			self.set()
		elif self.ball.pos[0]-self.ball.rad>=self.game.screensize[0]:
			left_score+=1
			self.set()
		# update the score depending on whether it has changed or not
		self.left_score.change(str(left_score))
		self.right_score.change(str(right_score))
		if left_score >= 10 or right_score >= 10:
			self.game.quit()
		self.game.render()
