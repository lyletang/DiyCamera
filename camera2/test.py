import ctypes
import multiprocessing
so = ctypes.CDLL("./libhello.so")
if __name__ == '__main__':
	t = multiprocessing.Process(target=so.turnOnTwo)
	t.start()

