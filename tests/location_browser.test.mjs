import test from 'node:test'; import assert from 'node:assert/strict';
import { createClient, SearchInteraction, fixtureResult, messages } from '../examples/browser-location-autocomplete/client.mjs';
test('publishable auth and inspector never expose credentials; secrets rejected', async () => {
 assert.throws(() => createClient({ fixture: false, publishableToken: 'gk_SECRET' }), /publishable/);
 assert.throws(() => createClient({ fixture: true, publishableToken: 'gk_SECRET' }), /publishable/);
 const inspect=[];let header;const client=createClient({ fixture:false,publishableToken:'gpk_test_SYNTHETIC',onRequest: item=>inspect.push(item),fetcher:async (url,init)=>{header=init.headers;return{ok:true,status:200,json:async()=>fixtureResult};} });
 await client.retrieve('selected',{sessionToken:'session'});assert.equal(header['X-Gridics-Publishable-Key'],'gpk_test_SYNTHETIC');assert.ok(!JSON.stringify(inspect).includes('SYNTHETIC'));
});
test('debounce, session reuse, retrieve, clear, keyboard', async()=>{
 let pending,uuid=0;const calls=[],states=[];const client={suggest:async(q,o,c)=>{calls.push(['suggest',c.sessionToken]);return{suggestions:[{gridics_id:'a'}]};},retrieve:async(id,c)=>{calls.push(['retrieve',c.sessionToken]);return fixtureResult;}};
 const search=new SearchInteraction(client,s=>states.push(s),{uuid:()=>`session-${++uuid}`,setTimer:f=>{pending=f;return 1;},clearTimer:()=>{pending=null;}});
 search.search('a');assert.equal(pending,null);search.search('100');const old=pending;search.search('100 E');assert.notEqual(pending,old);await pending();search.search('100 Ex');await pending();assert.equal(calls[0][1],calls[1][1]);assert.ok(search.key('ArrowDown'));assert.equal(search.active,0);await search.select(0);assert.equal(calls[2][1],calls[0][1]);assert.equal(search.session,null);search.search('new');await pending();assert.notEqual(calls[3][1],calls[0][1]);search.search('');assert.equal(search.session,null);search.clear();assert.equal(search.session,null);assert.equal(states.at(-1).resolved,null);
});
test('late responses cannot replace current results; cancellation and public errors',async()=>{
 let pending,resolveOld;const updates=[];let calls=0;const client={suggest:async(q,o,{signal})=>{if(++calls===1)return new Promise(r=>resolveOld=r);return{suggestions:[]};}};const s=new SearchInteraction(client,u=>updates.push(u),{setTimer:f=>{pending=f;},clearTimer:()=>{}});s.search('old');const first=pending();s.search('new');await pending();resolveOld({suggestions:[{gridics_id:'stale'}]});await first;assert.deepEqual(s.rows,[]);assert.equal(updates.at(-1).status,'No results found.');s.key('Escape');assert.deepEqual(s.rows,[]);
 for(const status of [401,403,409,422,429,502,503])await assert.rejects(createClient({errorStatus:status}).suggest('100',{},{}),new RegExp(messages[status].replace(/[.*+?^${}()|[\]\\]/g,'\\$&')));
});

test('expired interaction starts a new UUID',async()=>{let now=0,pending,uuid=0;const calls=[];const search=new SearchInteraction({suggest:async(q,o,c)=>{calls.push(c.sessionToken);return{suggestions:[]};}},()=>{},{uuid:()=>`uuid-${++uuid}`,now:()=>now,setTimer:f=>{pending=f;},clearTimer:()=>{}});search.search('100');await pending();now=180001;search.search('100 E');await pending();assert.notEqual(calls[0],calls[1]);});

test('fixture quota carries shared component error code',async()=>{await assert.rejects(createClient({errorStatus:429}).suggest('100',{},{}),error=>error.code==='quota_exhausted');});

test('ArrowUp enters at last row and wraps',()=>{const s=new SearchInteraction({},()=>{});s.rows=[{gridics_id:'a'},{gridics_id:'b'},{gridics_id:'c'}];s.key('ArrowUp');assert.equal(s.active,2);s.key('ArrowDown');assert.equal(s.active,0);});

test('owning API session errors normalize for shared component renewal',async()=>{for(const code of ['invalid_location_session','location_session_closed','location_session_mismatch','location_session_call_limit']){const client=createClient({fixture:false,publishableToken:'gpk_test_SYNTHETIC',fetcher:async()=>({ok:false,status:400,json:async()=>({messages:[code]})})});await assert.rejects(client.suggest('100',{},{}),error=>error.code==='session_invalid'&&!error.message.includes(code));}});
