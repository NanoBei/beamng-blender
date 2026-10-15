assert(getMissionFilename():find('/gridmap_v2/',1,true),'Load Gridmap V2 first')
loadJsonMaterialsFile('/art/hometown_hairpin_v3/main.materials.json')
loadJsonMaterialsFile('/art/china_subject2_v1/main.materials.json')
loadJsonMaterialsFile('/art/codex_connected_v2_width130/main.materials.json')
local current=scenetree.findObject('CodexConnectedV3Innerfill')
if not current then
  local old=scenetree.findObject('CodexConnectedV2Width130');if old then old:delete() end
  current=assert(spawnPrefab('CodexConnectedV3Innerfill','/art/codex_connected_v3_innerfill/connected.prefab.json','0 0 0','0 0 1 0','1 1 1'))
  scenetree.MissionGroup:addObject(current)
end
local proxy=scenetree.findObject('hairpin3_guardrails_collision');if proxy then proxy:setRenderEnabled(false) end
be:reloadCollision()
return current:getID()
