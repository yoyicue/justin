#
# Copyright 2012, Martin Owens <doctormo@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Rewritten from scratch, but based on the code from gnome-schedual by:
# - Philip Van Hoof <me at pvanhoof dot be>
# - Gaute Hope <eg at gaute dot vetsj dot com>
# - Kristof Vansant <de_lupus at pandora dot be>
#
EXAMPLE_USE = """
from crontab import CronTab
import sys

cron = CronTab()
job  = cron.new(command='/usr/bin/echo')

job.minute.during(5,50).every(5)
job.hour.every(4)

job.dow.on('SUN')
job.month.during('APR', 'NOV')

job2 = cron.new(command='/foo/bar',comment='SomeID')
job2.every_reboot()

list = cron.find_command('bar')
job3 = list[0]
job3.clear()
job3.minute.every(1)

sys.stdout.write(str(cron.render()))

for job4 in cron.find_command('echo'):
    sys.stdout.write(job4)

for job5 in cron:
    sys.stdout.write(job5)

cron.remove_all('echo')
cron.remove_all('/foo/bar')
cron.write()
"""

import os, re, sys
import tempfile

__version__ = '1.2'

CRONCMD = "/usr/bin/crontab"
ITEMREX = re.compile('^\s*([^@#\s]+)\s+([^@#\s]+)\s+([^@#\s]+)' +
    '\s+([^@#\s]+)\s+([^@#\s]+)\s+([^#\n]*)(\s+#\s*([^\n]*)|$)')
SPECREX = re.compile('@(\w+)\s([^#\n]*)(\s+#\s*([^\n]*)|$)')
DEVNULL = ">/dev/null 2>&1"

MONTH_ENUM = [ None,
    'jan', 'feb', 'mar', 'apr', 'may',
    'jun', 'jul', 'aug', 'sep', 'oct',
    'nov', 'dec',
]
WEEK_ENUM  = [
    'sun', 'mon', 'tue', 'wed', 'thu',
    'fri', 'sat', 'sun',
]

SPECIALS = {
    "reboot"  : '@reboot',
    "hourly"  : '0 * * * *',
    "daily"   : '0 0 * * *',
    "weekly"  : '0 0 * * 0',
    "monthly" : '0 0 1 * *',
    "yearly"  : '0 0 1 1 *',
    "annually": '0 0 1 1 *',
    "midnight": '0 0 * * *'
}

S_INFO = [
    { 'name' : 'Minutes',      'max_v' : 59, 'min_v' : 0 },
    { 'name' : 'Hours',        'max_v' : 23, 'min_v' : 0 },
    { 'name' : 'Day of Month', 'max_v' : 31, 'min_v' : 1 },
    { 'name' : 'Month',        'max_v' : 12, 'min_v' : 1, 'enum' : MONTH_ENUM },
    { 'name' : 'Day of Week',  'max_v' : 7,  'min_v' : 0, 'enum' : WEEK_ENUM },
]

# Detect Python3
import platform
py3 = platform.python_version()[0] == '3'

if py3:
    unicode = str
    basestring = str



class CronTab(object):
    """
    Crontab object which can access any time based cron using the standard.

    user    - Set the user of the crontab (defaults to $USER)
    tab     - Use a string variable as the crontab instead of installed crontab
    tabfile - Use a file for the crontab instead of installed crontab
    compat  - Force disable some features for SunOS (automatic).

    """
    def __init__(self, user=None, tab=None, tabfile=None, compat=False):
        self.user  = user
        self.root  = ( os.getuid() == 0 )
        self.lines = None
        self.crons = None
        self.filen = None
        # Detect older unixes and help them out.
        self.compat = compat or os.uname()[0] == "SunOS"
        self.intab = tab
        self.read(tabfile)

    def read(self, filename=None):
        """
        Read in the crontab from the system into the object, called
        automatically when listing or using the object. use for refresh.
        """
        self.crons = []
        self.lines = []
        if self.intab:
          lines = self.intab.split('\n')
        elif filename:
          self.filen = filename
          with open(filename, 'r') as fhl:
              lines = fhl.readlines()
        else:
          lines = os.popen(self._read_execute()).readlines()
        for line in lines:
            cron = CronItem(line, compat=self.compat)
            if cron.is_valid():
                self.crons.append(cron)
                self.lines.append(cron)
            else:
                self.lines.append(line.replace('\n',''))

    def write(self, filename=None):
        """Write the crontab to the system. Saves all information."""
        if filename:
            self.filen = filename

        # Add to either the crontab or the internal tab.
        if self.intab != None:
          self.intab = self.render()
          # And that's it if we never saved to a file
          if not self.filen:
              return

        if self.filen:
            fileh = open(self.filen, 'w')
        else:
            filed, path = tempfile.mkstemp()
            fileh = os.fdopen(filed, 'w')

        fileh.write(self.render())
        fileh.close()

        if not self.filen:
            # Add the entire crontab back to the user crontab
            os.system(self._write_execute(path))
            os.unlink(path)

    def render(self):
        """Render this crontab as it would be in the crontab."""
        crons = []
        for cron in self.lines:
            if type(cron) == CronItem and not cron.is_valid():
                crons.append("# " + unicode(cron))
                sys.stderr.write(
                    "Ignoring invalid crontab line `%s`\n" % str(cron))
                continue
            crons.append(unicode(cron))
        result = '\n'.join(crons)
        if result and result[-1] not in [ '\n', '\r' ]:
            result += '\n'
        return result

    def new(self, command='', comment=''):
        """
        Create a new cron with a command and comment.

        Returns the new CronItem object.
        """
        item = CronItem(command=command, meta=comment, compat=self.compat)
        self.crons.append(item)
        self.lines.append(item)
        return item

    def find_command(self, command):
        """Return a list of crons using a command."""
        result = []
        for cron in self.crons:
            if cron.command.match(command):
                result.append(cron)
        return result

    def remove_all(self, command):
        """Removes all crons using the stated command."""
        l_value = self.find_command(command)
        for c_value in l_value:
            self.remove(c_value)

    def remove(self, item):
        """Remove a selected cron from the crontab."""
        self.crons.remove(item)
        self.lines.remove(item)

    def _read_execute(self):
        """Returns the command line for reading a crontab"""
        return "%s -l%s" % (CRONCMD, self._user_execute())

    def _write_execute(self, path):
        """Return the command line for writing a crontab"""
        return "%s %s%s" % (CRONCMD, path, self._user_execute())

    def _user_execute(self):
        """User command switches to append to the read and write commands."""
        if self.user:
            return ' -u %s' % str(self.user)
        return ''

    def __iter__(self):
        return self.crons.__iter__()

    def __unicode__(self):
        return self.render()


class CronItem(object):
    """
    An item which objectifies a single line of a crontab and
    May be considered to be a cron job object.
    """
    def __init__(self, line=None, command='', meta='', compat=False):
        self.valid = False
        self.slices  = []
        self.special = False
        self.compat  = compat
        self.set_slices()
        self._meta   = meta
        if line:
            self.parse(line)
        elif command:
            self.command = CronCommand(unicode(command))
            self.valid = True

    def parse(self, line):
        """Parse a cron line string and save the info as the objects."""
        result = ITEMREX.findall(line)
        if result:
            o_value = result[0]
            self.command = CronCommand(o_value[5])
            self._meta   = o_value[7]
            self.set_slices( o_value )
            self.valid = True
        elif line.find('@') < line.find('#') or line.find('#')==-1:
            result = SPECREX.findall(line)
            if result and result[0][0] in SPECIALS:
                o_value = result[0]
                self.command = CronCommand(o_value[1])
                self._meta   = o_value[3]
                value = SPECIALS[o_value[0]]
                if value.find('@') != -1:
                    self.special = value
                else:
                    self.set_slices( value.split(' ') )
                self.valid = True

    def set_slices(self, o_value=None):
        """Set the values of this slice set"""
        self.slices = []
        for i_value in range(0, 5):
            if not o_value:
                o_value = [None, None, None, None, None]
            self.slices.append(
                CronSlice(compat=self.compat, value=o_value[i_value],
                    **S_INFO[i_value]))

    def is_valid(self):
        """Return true if this slice set is valid"""
        return self.valid

    def render(self):
        """Render this set slice to a string"""
        time = ''
        if not self.special:
            slices = []
            for i in range(0, 5):
                slices.append(unicode(self.slices[i]))
            time = ' '.join(slices)
        if self.special or time in SPECIALS.values():
            if self.special:
                time = self.special
            else:
                time = "@%s" % SPECIALS.keys()[SPECIALS.values().index(time)]

        result = "%s %s" % (time, unicode(self.command))
        if self.meta():
            result += " # " + self.meta()
        return result


    def meta(self, value=None):
        """Return or set the meta value to replace the set values"""
        if value:
            self._meta = value
        return self._meta

    def every_reboot(self):
        """Set to every reboot instead of a time pattern"""
        self.special = '@reboot'

    def clear(self):
        """Clear the special and set values"""
        self.special = None
        for slice_v in self.slices:
            slice_v.clear()

    @property
    def minute(self):
        """Return the minute slice"""
        return self.slices[0]

    @property
    def hour(self):
        """Return the hour slice"""
        return self.slices[1]

    @property
    def dom(self):
        """Return the day-of-the month slice"""
        return self.slices[2]

    @property
    def month(self):
        """Return the month slice"""
        return self.slices[3]

    @property
    def dow(self):
        """Return the day of the week slice"""
        return self.slices[4]

    def __repr__(self):
        return "<CronJob '%s'>" % str(self)

    def __eq__(self, value):
        return str(self) == str(value)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return self.render()


class CronSlice(object):
    """Cron slice object which shows a time pattern"""
    def __init__(self, name, min_v, max_v, enum=None, value=None, compat=False):
        self.name   = name
        self.min    = min_v
        self.max    = max_v
        self.enum   = enum
        self.compat = compat
        self.parts  = []
        if value:
            self._set_value(value)

    def _set_value(self, value):
        """Set values into the slice."""
        self.parts = []
        for part in value.split(','):
            if part.find("/") > 0 or part.find("-") > 0 or part == '*':
                self.parts.append( self.get_range( part ) )
            else:
                try:
                    self.parts.append( self._v(part) )
                except ValueError:
                    raise ValueError('Unknown cron time part for %s: %s' % (
                        self.name, part))

    def render(self, resolve=False):
        """Return the slice rendered as a crontab.

        resolve - return integer values instead of enums (default False)

        """
        if len(self.parts) == 0:
            return '*'
        return _render_values(self.parts, ',', resolve)

    def __repr__(self):
        return "<CronSlice '%s'>" % str(self)

    def __eq__(self, value):
        return str(self) == str(value)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return self.render()

    def every(self, n_value):
        """Set the every X units value"""
        self.parts = [ self.get_range( int(n_value) ) ]
        return self.parts[0]

    def on(self, *n_value):
        """Set the on the time value."""
        for av in n_value:
            self.parts += self._v(av),

    def during(self, vfrom, vto):
        """Set the During value, which sets a range"""
        self.parts.append(self.get_range(self._v(vfrom), self._v(vto)))
        return self.parts[-1]

    def clear(self):
        """clear the slice ready for new vaues"""
        self.parts = []

    def get_range(self, *vrange):
        """Return a cron range for this slice"""
        return CronRange( self, *vrange )

    def _v(self, v):
        """Support wrapper for enumerations and check for range"""
        try:
            out = CronValue(v, self.enum)
        except ValueError:
            raise ValueError("Unrecognised value '%s' for '%s'" % (v, self.name))
        except KeyError:
            raise KeyError("No enumeration for '%s' found '%s'" % (self.name, v))

        if int(out) < self.min and int(out) > self.max:
            raise ValueError("Invalid value '%s', expected %d-%d for %s" % (
                str(value), self.min, self.max, self.name))
        return out


class CronValue(object):
    """Returns a value as int (pass-through) or a special enum value"""
    def __new__(cls, value, enums):
        if isinstance(value, int):
            return value
        elif str(value).isdigit():
            return int(str(value))
        if not enums:
            raise KeyError("No enumeration allowed")
        return object.__new__(cls, str(value), enums)

    def __init__(self, value, enums): # throws ValueError
        self.enum = value
        self.value = enums.index(value.lower())

    def __lt__(self, value):
        return self.value < int(value)
    def __repr__(self):
        return str(self)
    def __str__(self):
        return self.enum
    def __int__(self):
        return self.value


def _render_values(values, sep=',', resolve=False):
    """Returns a rendered list, sorted and optionally resolved"""
    if len(values) > 1:
        values.sort()
    return sep.join([ _render(val, resolve) for val in values ])

def _render(value, resolve=False):
    """Return a single value rendered"""
    if isinstance(value, CronRange):
        return value.render(resolve)
    if resolve:
        return str(int(value))
    return str(value)



class CronRange(object):
    """A range between one value and another for a time range."""
    def __init__(self, vslice, *vrange):
        self.slice = vslice
        self.seq   = 1

        if not vrange:
            self.all()
        elif isinstance(vrange[0], basestring):
            self.parse(vrange[0])
        elif isinstance(vrange[0], int) or isinstance(vrange[0], CronValue):
            if len(vrange) == 2:
                (self.vfrom, self.vto) = vrange
            else:
                self.seq = vrange[0]
                self.all()

    def parse(self, value):
        """Parse a ranged value in a cronjob"""
        if value.find('/') > 0:
            value, seq = value.split('/')
            self.seq = int(seq)
        if value.find('-') > 0:
            vfrom, vto = value.split('-')
            self.vfrom = self.slice._v(vfrom)
            self.vto  = self.slice._v(vto)
        elif value == '*':
            self.all()
        else:
            raise ValueError('Unknown cron range value %s' % value)

    def all(self):
        """Set this slice to all units between the miniumum and maximum"""
        self.vfrom = self.slice.min
        self.vto  = self.slice.max

    def render(self, resolve=False):
        """Render the ranged value for a cronjob"""
        value = '*'
        if int(self.vfrom) > self.slice.min or int(self.vto) < self.slice.max:
            value = _render_values([self.vfrom, self.vto], '-', resolve)
        if self.seq != 1:
            value += "/%d" % self.seq
        if value != '*' and self.slice.compat:
            value = ','.join(map(str, range(self.vfrom, self.vto+1, self.seq)))
        return value

    def every(self, value):
        """Set the sequence value for this range."""
        self.seq = int(value)

    def __lt__(self, value):
        return int(self.vfrom) < int(value)

    def __int__(self):
        return int(self.vfrom)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return self.render()


class CronCommand(object):
    """Reprisent a cron command as an object."""
    def __init__(self, line):
        self._command = line

    def match(self, command):
        """Match the command given"""
        if command in self._command:
            return True
        return False

    def command(self):
        """Return the command line"""
        return self._command

    def __str__(self):
        """Return a string as a value"""
        return self.__unicode__()

    def __unicode__(self):
        """Return unicode command line value"""
        return self.command()

