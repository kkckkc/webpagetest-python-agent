import ConfigParser
import io
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile


DEFAULT_JOB_PROPERTIS = {
    "runs": "1",
    "Capture Video": "0"
}


class ConfigurationParser:
    def __init__(self, config, job_properties):
        self.config = ConfigParser.ConfigParser()
        self.config.readfp(io.BytesIO(config))

        # Add defaults
        self.config.add_section("Job")
        for k, v in DEFAULT_JOB_PROPERTIS.iteritems():
            self.config.set("Job", k, v)

        # Add job properties
        job = ConfigParser.ConfigParser()
        job.readfp(io.BytesIO(job_properties))
        for s in job.sections():
            if not self.config.has_section(s):
                self.config.add_section(s)
            for k in job.options(s):
                self.config.set(s, k, job.get(s, k))

    def resolve(self, section, property):
        def parse_expression(s):
            placeholder_string = s if type(s) == str else s.group(1)

            # Scoped properties, matching "Job.runs" and "Job.[Capture Video]"
            m = re.match("^(\w+)\\.\\[?([\w ]+)\\]?$", placeholder_string)
            if m:
                return self.resolve(m.group(1), m.group(2))

            # Unscoped properties, matching "runs" and "[Capture Video]"
            m = re.match("^\\[?([\w ]+)\\]?$", placeholder_string)
            if m:
                return self.resolve(section, m.group(1))

            # Conditionals, matching "video? Base.videoCmdLine" or "Base.[Capture Video]? videoCmdLine"
            m = re.match("^\\[?([\w\\. ]+)\\]?\\? (.*)$", placeholder_string)
            if m:
                condition = parse_expression(m.group(1))
                if condition == "" or condition.lower() == "false" or condition == "0":
                    return ""
                else:
                    return parse_expression(m.group(2))

            raise Exception("Cannot parse '%s'" % placeholder_string)

        def resolve_property(property, section):
            if self.config.has_option(section, property):
                return self.config.get(section, property)
            elif self.config.has_option(section, "_extends"):
                return resolve_property(property, self.config.get(section, "_extends"))
            else:
                raise Exception("Cannot find property '%s.%s'" % (section, property))

        return re.sub("\\${(.*?)}", parse_expression, resolve_property(property, section))


class Launcher:
    def __init__(self, config_file, job_file, result_directory):
        self.config_file = config_file
        self.job_file = job_file
        self.result_directory = result_directory

    def launch(self):
        with open(self.job_file, "r") as f:
            job = "[Job]\n%s" % f.read()

        with open(self.config_file, "r") as f:
            config = f.read()

        parser = ConfigurationParser(config, job)
        browser = parser.resolve("Job", "Browser")
        args = shlex.split(parser.resolve(browser, "cmdLine"))

        args.insert(0, sys.executable)
        args.insert(1, "wpt_run.py")


        # TODO: Complete
        print(args)

#        subprocess.check_output([
#            sys.executable,
#            "wpt_run.py",
#            ""], stderr=subprocess.STDOUT, env=os.environ.copy())


if __name__ == '__main__':

    config = (
        "[Base]\n"
        "cmdLine = -r ${numberOfRuns}\n"
        "videoCmdLine = -p FfmpegVideoCapture\n"
        "video = ${Job.[Capture Video]}\n"
        "numberOfRuns = ${Job.runs}\n"
        "\n"
        "[BaseChrome]\n"
        "_extends = Base\n"
        "cmdLine = ${Base.cmdLine} -p ChromeWebDriver --chromedriver ${chromeDriverPath} ${video? videoCmdLine}\n"
        "\n"
        "[Chrome]\n"
        "_extends = BaseChrome\n"
        "chromeDriverPath = /Users/magnus/Desktop/Inbox/chromedriver"
    )

    job = (
        "Test ID=160912_AD_1\n"
        "browser=Chrome\n"
        "url=http://www.ikea.com/ie/en/"
    )

    dir = tempfile.mkdtemp(prefix='tmp_wpt_')
    try:
        job_path = os.path.join(dir, "test.job")
        config_path = os.path.join(dir, "base.ini")

        with open(job_path, "w") as job_file:
            job_file.write(job)

        with open(config_path, "w") as config_file:
            config_file.write(config)

        l = Launcher(config_path, job_path, dir)
        l.launch()

    finally:
        shutil.rmtree(dir)
