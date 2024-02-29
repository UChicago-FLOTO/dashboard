var EnvironmentComponent = {
  props: ["modelValue"],
  setup(props, ctx) {
    props.modelValue.environment = {}
    return { 
      environment_component_obj: props.modelValue,
      delete_item(name){
        delete props.modelValue.environment[name]
        ctx.emit('update:modelValue', props.modelValue)
      },
      add_item(){
        let env_com_obj = props.modelValue
        if(env_com_obj.new_key){
          env_com_obj.environment[env_com_obj.new_key] = env_com_obj.new_value
          env_com_obj.new_key = ""
          env_com_obj.new_value = ""
          ctx.emit('update:modelValue', props.modelValue)
        }
      }
    }
  },
  template: `
    <div class="q-pa-sm">
      <h5>Environment</h5>
      <q-markup-table>
        <thead>        
          <tr>
            <th class="text-left">Key</th>
            <th class="text-left">Value</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(value, name, index) in environment_component_obj.environment">
            <td>{{name}}</td>
            <td>{{value}}</td>
            <td>
              <q-btn
                color="negative"
                icon-right="delete"
                no-caps
                flat
                dense
                @click="delete_item(name)"
              />
            </td>
          </tr>
          <tr>
              <td>
                <q-input 
                  v-model="environment_component_obj.new_key" label="Key"
                />
              </td>
              <td>
                <q-input 
                  v-model="environment_component_obj.new_value" label="Value" 
                />
              </td>
              <td>
                <q-btn
                  icon-right="add"
                  no-caps
                  flat
                  dense
                  @click="add_item()"
                />
              </td>
          </tr>
        </tbody>
      </q-markup-table>
    </div>
    `
}
  