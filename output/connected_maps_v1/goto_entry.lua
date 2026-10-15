dofile('/art/codex_connected_v1/load.lua')
local v=assert(be:getPlayerVehicle(0),'Player vehicle missing')
v:queueLuaCommand('ai.setMode("disabled")')
spawn.safeTeleport(v,vec3(-1730,-1470,101.4),quatFromDir(vec3(1,0,0)),nil,nil,nil,nil,true)
v:queueLuaCommand('input.event("parkingbrake",1,1)')
core_camera.setByName(0,'orbit')
return 'Connected course: west entry, facing subject-two gate'
