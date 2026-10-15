assert(getMissionFilename():find('/gridmap_v2/', 1, true), 'Expected Gridmap V2')
local road = assert(scenetree.findObject('CodexHairpinRoad'), 'Road prefab missing')
for _,part in ipairs({'road', 'terrain', 'earth_sides', 'guardrails'}) do
  assert(FS:fileExists('/art/hairpin_road/shapes/'..part..'.dae'), 'Missing '..part)
end
for _,name in ipairs({'hp_asphalt','hp_terrain_grass','hp_terrain_soil','hp_earth_side','hp_guardrail'}) do
  assert(scenetree.findObject(name), 'Material missing: '..name)
end
local height = 150 - castRayStatic(vec3(-163,-106,150), vec3(0,0,-1),60)
assert(math.abs(height - 114) < 0.05, 'Road entrance collision height incorrect')
local vehicle = assert(be:getPlayerVehicle(0), 'Player vehicle missing')
return jsonEncode({prefabId=road:getID(),collisionHeight=height,vehiclePosition=vehicle:getPosition(),vehicleVelocity=vehicle:getVelocity(),level=getMissionFilename()})
