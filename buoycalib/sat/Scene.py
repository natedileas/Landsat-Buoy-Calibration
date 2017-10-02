

class Scene(object):
    def __init__(self, sat, date='', _dir='', metadata={}):
        self.satellite = sat
        self.date = date
        self.directory = _dir
        self.metadata = metadata

    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, m):
        self._metadata = m
        self.__dict__.update(m)


def id_to_scene(scene_id, scene_type=''):
    if len(scene_id) == 21:
        s = Scene('L' + scene_id[2:3])
        s.path = scene_id[3:6]
        s.row = scene_id[6:9]
        s.id = scene_id
    elif len(scene_id) == 40:
        s = Scene('c{0}/L{1}'.format(scene_id[-4], scene_id[3]))
        s.path = scene_id[10:13]
        s.row = scene_id[13:16]
        s.id = scene_id
    else:
        raise Exception('Received incorrect scene: {0}'.format(scene_id))

    return s
