import os
import shutil
from collections import namedtuple


class Session:
    def __init__(self, run_count, result_dir, script="", url=""):
        self.run_count = run_count
        self.script = script
        self.url = url
        self.result_dir = result_dir

    def __repr__(self):
        return "Session(run_count=%d, url=%s, script=%s)" % (self.run_count, self.url, self.script)


class Run:
    def __init__(self, current):
        self.current = current

    def __repr__(self):
        return "Run(current=%d)" % (self.current)


class View:
    def __init__(self, is_first, is_repeat):
        self.is_repeat = is_repeat
        self.is_first = is_first

    def __repr__(self):
        return "View(is_first=%r, is_repeat=%r)" % (self.is_first, self.is_repeat)


class Step:
    def __init__(self, index, name):
        self.index = index
        self.name = name

    def __repr__(self):
        return "Step(index=%d, name=%s)" % (self.index, self.name)


class ResultDirectory:
    file_record = namedtuple("file_record", "file,name,run,step,view")
    mapping = namedtuple("mapping", "file,order,prefix,delimiter,repeat")

    MAPPING = [
        mapping(file="histograms.json.gz", order="run,step,repeat", prefix=True, delimiter=".", repeat="number"),
        mapping(file="video", order="run,repeat,step", prefix=False, delimiter="_", repeat="text_lc"),
        mapping(file="test.job", order=None, prefix=False, delimiter=None, repeat=None),
        mapping(file="*", order="run,repeat,step", prefix=True, delimiter="_", repeat="text")
    ]

    def __init__(self, folder):
        self.files = []
        self.folder = folder
        if os.path.exists(self.folder):
            shutil.rmtree(self.folder)
        os.mkdir(self.folder)

    # TODO: Change to contextmanager
    def open_file(self, name, run=None, view=None, step=None):
        return open(self.get_file(name, run, view, step), "w")

    def get_file(self, name, run, view, step):
        f = self._to_filename(name,
                              None if run is None else run.current,
                              None if step is None else step.index,
                              None if view is None else view.is_repeat)
        record = ResultDirectory.file_record(f, name, run, step, view)
        if record not in self.files:
            self.files.append(record)
        return os.path.join(self.folder, f)

    def open_associated_file(self, name, file_record):
        self.open_file(name, file_record.run, file_record.view, file_record.step)

    def get_associated_file(self, name, file_record):
        return self.get_file(name, file_record.run, file_record.view, file_record.step)

    def get_files(self, name):
        return [f for f in self.files if f.name == name]

    def _to_filename(self, name, run_id, step_id, repeat):
        for m in ResultDirectory.MAPPING:
            if name == m.file or m.file == '*':
                if m.order is None:
                    assert run_id is None
                    assert step_id is None
                    assert repeat is None
                    return name
                else:
                    elements = []
                    for e in m.order.split(","):
                        if e == 'run':
                            elements.append(str(run_id))
                        elif e == 'step' and step_id >= 2:
                            elements.append(str(step_id))
                        elif e == 'repeat':
                            if m.repeat == 'number':
                                elements.append("1" if repeat else "0")
                            elif m.repeat == 'text' and repeat:
                                elements.append("Cached")
                            elif m.repeat == 'text_lc' and repeat:
                                elements.append("cached")

                    if m.prefix:
                        elements.append(name)
                    else:
                        elements.insert(0, name)

                    return m.delimiter.join(elements)
