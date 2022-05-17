class ObjectPool:
    '''An object resource manager.
    
    Inspiration: https://gist.github.com/pazdera/1124839
    '''

    __instance = None
    __resources = list()

    def __init__(self) -> None:
        if ObjectPool.__instance != None:
            raise NotImplemented('This is a singleton class.')

    @staticmethod
    def get_instance():
        if ObjectPool.__instance == None:
            ObjectPool.__instance = ObjectPool()

        return ObjectPool.__instance

    def borrow_resource(self):
        if len(self.__resources) > 0:
            # pop from front
            return self.__resources.pop(0)
        else:
            print('No free resource currently.')

    def return_resource(self, resource):
        self.__resources.append(resource)
    
    def set_resource(self, resources):
        self.__resources = resources

    def get_total_resource(self):
        return len(self.__resources)