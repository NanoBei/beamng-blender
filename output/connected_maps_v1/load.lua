assert(getMissionFilename():find('/gridmap_v2/',1,true),'Load Gridmap V2 first')
loadJsonMaterialsFile('/art/hometown_hairpin_v3/main.materials.json')
loadJsonMaterialsFile('/art/china_subject2_v1/main.materials.json')
loadJsonMaterialsFile('/art/codex_connected_v1/main.materials.json')
local existing=scenetree.findObject('CodexConnectedV1')
if not existing then
  for _,name in ipairs({'CodexHometownV3','CodexSubject2V1'}) do
    local old=scenetree.findObject(name)
    if old then old:delete() end
  end
  existing=assert(spawnPrefab('CodexConnectedV1','/art/codex_connected_v1/connected.prefab.json','0 0 0','0 0 1 0','1 1 1'))
  scenetree.MissionGroup:addObject(existing)
end
local proxy=scenetree.findObject('hairpin3_guardrails_collision')
if proxy then proxy:setRenderEnabled(false) end
be:reloadCollision()
return jsonEncode({id=existing:getID(),name=existing:getName()})
