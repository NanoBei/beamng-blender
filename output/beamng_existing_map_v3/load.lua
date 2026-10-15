assert(getMissionFilename():find('/gridmap_v2/',1,true), 'Expected Gridmap V2')
assert(not scenetree.findObject('CodexHairpinRoad'), 'Old hairpin occupies this location; preserve and relocate it before loading V3')
loadJsonMaterialsFile('/art/hometown_hairpin_v3/main.materials.json')
core_environment.reloadGroundModels()
assert(core_environment.groundModels.HP3_CONCRETE, 'Concrete ground model missing')
local road = scenetree.findObject('CodexHometownV3')
if not road then
  road = assert(spawnPrefab('CodexHometownV3', '/art/hometown_hairpin_v3/hometown.prefab.json', '-1580 -1490 114', '0 0 1 0', '1 1 1'), 'Prefab failed')
  scenetree.MissionGroup:addObject(road)
end
for _, id in ipairs(scenetree.findClassObjects('TSStatic')) do
  local obj = scenetree.findObject(id)
  if obj:getName():find('hairpin3_', 1, true) == 1 then
    obj:setRenderEnabled(obj:getName() ~= 'hairpin3_guardrails_collision')
  end
end
be:reloadCollision()
return jsonEncode({name=road:getName(),id=road:getID(),position=road:getPosition()})
