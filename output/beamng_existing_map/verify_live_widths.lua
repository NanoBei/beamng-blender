local sections={
  {label='Main 4.00 m',c={7,44},n={0,1},expected=4},
  {label='Slope 3.33 m',c={23.688309,38.083344},n={0.422618262,0.906307787},expected=3.33},
  {label='Slope 3.33 m',c={20.358943,30.330398},n={0.173648178,-0.984807753},expected=3.33},
  {label='Slope 3.33 m',c={26.469454,21.213348},n={0.422618262,0.906307787},expected=3.33}
}
local results={}
for i,s in ipairs(sections) do
  local function sample(t)
    local x,y=s.c[1]-170+t*s.n[1],s.c[2]-150+t*s.n[2]
    return castRay(vec3(x,y,140),vec3(x,y,99),true,false)
  end
  local function isRoad(t)
    local r=sample(t)
    return r and tostring(r.obj)=='hairpin_road'
  end
  assert(isRoad(0),'Section center is not road: '..i)
  local edges={}
  for _,sign in ipairs({-1,1}) do
    local lo,hi=0,2.4
    assert(not isRoad(sign*hi),'Outside point is still road')
    for j=1,19 do local mid=(lo+hi)/2; if isRoad(sign*mid) then lo=mid else hi=mid end end
    edges[#edges+1]=sign*(lo+hi)/2
  end
  local width=edges[2]-edges[1]
  assert(math.abs(width-s.expected)<.02,'Wrong collision width at section '..i..': '..width)
  results[#results+1]={label=s.label,collisionWidthM=width}
  local p1,p2=sample(edges[1]+.025).pt,sample(edges[2]-.025).pt
  extensions.mcp_tools.debug_draw({id='hairpin_width_'..i,kind='line',from={x=p1.x,y=p1.y,z=p1.z+.12},to={x=p2.x,y=p2.y,z=p2.z+.12},color={0.1,1,0.4,1},label=s.label,ttl=120})
end
return jsonEncode(results)
