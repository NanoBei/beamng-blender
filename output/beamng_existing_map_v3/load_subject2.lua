assert(getMissionFilename():find('/gridmap_v2/',1,true), 'Expected Gridmap V2')
loadJsonMaterialsFile('/art/china_subject2_v1/main.materials.json')
core_environment.reloadGroundModels()
assert(core_environment.groundModels.C1V1_CONCRETE, 'Concrete ground model missing')
local site = scenetree.findObject('CodexSubject2V1')
if not site then
  site = assert(spawnPrefab('CodexSubject2V1', '/art/china_subject2_v1/subject2.prefab.json', '-1700 -1500 101', '0 0 1 0', '1 1 1'), 'Prefab failed')
  scenetree.MissionGroup:addObject(site)
end
for _, id in ipairs(scenetree.findClassObjects('TSStatic')) do
  local obj = scenetree.findObject(id)
  if obj:getName():find('c1_', 1, true) == 1 then obj:setRenderEnabled(true) end
end
be:reloadCollision()
return jsonEncode({name=site:getName(),id=site:getID(),position=site:getPosition()})
