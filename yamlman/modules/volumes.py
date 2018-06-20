import base


class Volumes(base.RenderBase):

    def render(self, obj, data):
        if isinstance(obj['trigger']['volumes'], list):
            obj['trigger']['volumes'].append(data)
        else:
            raise Exception('Volumes must be a list')
