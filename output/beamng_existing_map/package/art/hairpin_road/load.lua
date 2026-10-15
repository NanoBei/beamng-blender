-- Run in GE Lua: dofile('/art/hairpin_road/load.lua')
assert(getMissionFilename():find('/gridmap_v2/', 1, true), 'Load Gridmap V2 first')
loadJsonMaterialsFile('/art/hairpin_road/main.materials.json')
if not scenetree.findObject('CodexHairpinRoad') then
  local obj = spawnPrefab('CodexHairpinRoad', '/art/hairpin_road/hairpin.prefab.json', '-170 -150 114', '0 0 1 0', '1 1 1')
  assert(obj, 'Road prefab did not load')
  scenetree.MissionGroup:addObject(obj)
  be:reloadCollision()
end
local vehicle = be:getPlayerVehicle(0)
if vehicle then
  spawn.safeTeleport(vehicle, vec3(-163, -106, 114.5), quatFromDir(vec3(1, 0, 0)), nil, nil, nil, nil, true)
  core_camera.setByName(0, 'orbit')
end
return 'Hairpin road ready'
