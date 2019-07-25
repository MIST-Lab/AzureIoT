import pygame

pygame.init()
pygame.mixer.init(44100)
pygame.mixer.music.load('Basketball_Dribb.mp3')
pygame.mixer.music.play()
pygame.event.wait()

