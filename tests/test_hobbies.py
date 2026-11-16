"""Exercise the after-hours controller without a server or wall-clock fixtures."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HobbiesControllerTests(unittest.TestCase):
    def test_fetch_failure_language_and_controls(self):
        script = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('assets/hobbies.js','utf8');
async function run(fail) {
    const events={},requests=[],renders=[],intervals=[];
    const status={textContent:''},duration={disabled:true,addEventListener:(key,fn)=>events[key]=fn};
    const doc={hidden:false,documentElement:{lang:'pl'},
        getElementById:id=>id==='rideDuration'?duration:status,
        addEventListener:(key,fn)=>events[key]=fn};
    const weather={locations:{kat04bapp:{current:{},forecast:{intervals:[]}}}};
    const air={stations:[]};
    const context={document:doc,window:{RidePlanner:{render:(loc,a,failed)=>renders.push({loc,a,failed})}},
        AbortController,Date,
        setTimeout:()=>1,clearTimeout:()=>{},
        setInterval:fn=>intervals.push(fn),
        fetch:async(url,options)=>{
            requests.push(url);
            assert.equal(options.cache,'no-cache');
            assert.ok(options.signal);
            return {ok:!(fail&&url==='data.json'),status:503,json:async()=>url==='data.json'?air:weather};
        }};
    vm.runInNewContext(source,context);
    await new Promise(resolve=>setImmediate(resolve));
    assert.deepEqual(requests,['weather.json','data.json']);
    assert.equal(duration.disabled,false);
    assert.equal(renders.at(-1).failed,fail);
    assert.match(status.textContent,fail?/Nie udało/:/Open-Meteo/);
    doc.documentElement.lang='en';events['portfolio:language']();
    assert.match(status.textContent,fail?/could not/:/automatic refresh/);
    events.change();
    assert.equal(renders.at(-1).failed,fail);
    assert.equal(intervals.length,2);
    if(!fail) assert.equal(renders.at(-1).loc,weather.locations.kat04bapp);
}
(async()=>{await run(false);await run(true)})().catch(e=>{console.error(e);process.exit(1)});
"""
        result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
