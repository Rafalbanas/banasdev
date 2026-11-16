"""Boundary and malformed-data checks, independent of wall clock or network."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RideBoundaryTests(unittest.TestCase):
    def test_thresholds_and_untrusted_data(self):
        script = r"""
const assert = require('node:assert/strict');
const {evaluate,timeline} = require('./assets/ride-planner.js');
const now = Date.parse('2026-11-15T10:00:00Z');
const iso = n => new Date(n).toISOString();
function fixture() {
    const p = {temperature:18,wind_speed:10,precipitation:0,weather_code:0,precipitation_probability:0};
    return {
        location: {current:{...p,data_time_utc:iso(now),fetched_at_utc:iso(now)},
            forecast:{issued_at_utc:iso(now),intervals:Array.from({length:8},(_,i) => ({
                ...p,interval_start_utc:iso(now+i*900000),interval_end_utc:iso(now+(i+1)*900000)
            }))}},
        air:{measured_at:iso(now),air_index_level:'GOOD',pm25:{value:10},pm10:{value:15},
            stations:[{air_index_level:'GOOD'}]}
    };
}
function check(expected, mutate, duration=60) {
    const f=fixture(); mutate(f);
    assert.equal(evaluate(f.location,f.air,now,duration).state,expected);
}
for (const [key, value, expected] of [
    ['temperature',2,'avoid'], ['temperature',32,'avoid'],
    ['temperature',10,'go'], ['temperature',26,'go'],
    ['wind_speed',20,'go'], ['wind_speed',20.1,'caution'],
    ['precipitation',0.1,'caution'], ['precipitation',0.5,'avoid'],
    ['precipitation_probability',40,'caution'], ['precipitation_probability',70,'avoid'],
    ['weather_code',45,'caution'], ['weather_code',48,'avoid'],
    ['weather_code',95,'avoid'], ['snowfall',0.1,'avoid'],
    ['wind_speed','10','unknown'], ['temperature',null,'unknown'],
    ['precipitation_probability',101,'unknown'], ['weather_code',999,'unknown']
]) check(expected,f => f.location.forecast.intervals.forEach(p=>p[key]=value));
for (const level of ['UNKNOWN','SATISFACTORY',null])
    check('unknown',f=>f.air.stations[0].air_index_level=level);
check('caution',f=>f.air.stations[0].air_index_level='MODERATE');
check('avoid',f=>f.air.stations[0].air_index_level='SUFFICIENT');
check('unknown',f=>f.air.stations='bad');
check('unknown',f=>f.location.forecast.intervals[0]=null);
check('unknown',f=>f.location.forecast.intervals[1].interval_start_utc=iso(now));
check('unknown',f=>f.location.forecast.intervals[0].interval_end_utc='not a date');
check('unknown',f=>f.location.current.data_time_utc=iso(now+6*60000));
check('unknown',f=>f.location.forecast.issued_at_utc=iso(now-31*60000));
check('unknown',f=>f.air.measured_at=iso(now-181*60000));
check('unknown',f=>{},120);
// A storm at "now" must prevent "go", even with an otherwise dry forecast.
check('wait',f=>f.location.current.weather_code=95);
// No mutation: both page consumers may reuse the same fetched payload.
const f=fixture(), before=JSON.stringify(f);
evaluate(f.location,f.air,now,30);
assert.equal(JSON.stringify(f),before);
assert.equal(evaluate(null,null,now).state,'unknown');
// Timeline shares the rules but must retain explicit future holes.
let t=fixture();
assert.equal(timeline(t.location,t.air,now).length,8);
assert.ok(timeline(t.location,t.air,now).every(p=>p.state==='go'));
t.location.forecast.intervals[3].wind_speed=40;
assert.equal(timeline(t.location,t.air,now)[3].state,'avoid');
t.location.forecast.intervals[2].temperature=5;
assert.equal(timeline(t.location,t.air,now)[2].state,'caution');
t.location.forecast.intervals.splice(5,1);
assert.equal(timeline(t.location,t.air,now)[5].state,'unknown');
assert.equal(timeline(t.location,t.air,now,true).length,0);
assert.equal(timeline(null,null,now).length,0);
t=fixture();
t.air.stations[0].air_index_level='BAD';
assert.ok(timeline(t.location,t.air,now).every(p=>p.state==='avoid'));
t=fixture();
t.location.forecast.intervals.push({...t.location.forecast.intervals[5]});
assert.equal(timeline(t.location,t.air,now)[5].state,'unknown');
assert.equal(timeline(t.location,t.air,now+60000).length,9);
assert.equal(timeline(t.location,t.air,now+60000)[0].start,now+60000);
"""
        result = subprocess.run(["node", "-e", script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
