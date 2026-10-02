/* Built as i686, independently of the x64 Qt launcher. No disc/window required.
 * dlopen is deliberate: a missing Vulkan loader must produce a useful report. */
#define VK_NO_PROTOTYPES
#include <vulkan/vulkan.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void json_string(const char *s) {
    putchar('"');
    for (const unsigned char *p = (const unsigned char *)s; *p; ++p) {
        if (*p == '"' || *p == '\\') printf("\\%c", *p);
        else if (*p < 32) printf("\\u%04x", *p);
        else putchar(*p);
    }
    putchar('"');
}
static int failure(const char *message) {
    printf("{\"format\":1,\"bits\":%zu,\"devices\":[],\"error\":", sizeof(void *) * 8);
    json_string(message); puts("}"); return 2;
}
int main(void) {
    if (sizeof(void *) != 4) return failure("Graphics probe must be a 32-bit executable.");
    void *library = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
    if (!library) return failure("Cannot load libvulkan.so.1 in the 32-bit game environment.");
    PFN_vkGetInstanceProcAddr get = (PFN_vkGetInstanceProcAddr)dlsym(library, "vkGetInstanceProcAddr");
    if (!get) return failure("32-bit Vulkan loader is missing vkGetInstanceProcAddr.");
    PFN_vkCreateInstance create = (PFN_vkCreateInstance)get(VK_NULL_HANDLE, "vkCreateInstance");
    PFN_vkEnumerateInstanceVersion version = (PFN_vkEnumerateInstanceVersion)get(VK_NULL_HANDLE, "vkEnumerateInstanceVersion");
    uint32_t api = VK_API_VERSION_1_0;
    if (version) version(&api);
    if (!create || api < VK_API_VERSION_1_1) return failure("32-bit Vulkan loader does not support Vulkan 1.1.");
    VkApplicationInfo application = {.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO, .pApplicationName = "GD's Melee graphics check", .apiVersion = VK_API_VERSION_1_1};
    VkInstanceCreateInfo info = {.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO, .pApplicationInfo = &application};
    VkInstance instance;
    VkResult result = create(&info, NULL, &instance);
    char error[160];
    if (result != VK_SUCCESS) { snprintf(error, sizeof(error), "32-bit vkCreateInstance failed (VkResult %d). Check the installed 32-bit GPU drivers.", result); return failure(error); }
#define LOAD(type, name) type name = (type)get(instance, #name)
    LOAD(PFN_vkEnumeratePhysicalDevices, vkEnumeratePhysicalDevices);
    LOAD(PFN_vkGetPhysicalDeviceProperties, vkGetPhysicalDeviceProperties);
    LOAD(PFN_vkGetPhysicalDeviceQueueFamilyProperties, vkGetPhysicalDeviceQueueFamilyProperties);
    LOAD(PFN_vkEnumerateDeviceExtensionProperties, vkEnumerateDeviceExtensionProperties);
    LOAD(PFN_vkCreateDevice, vkCreateDevice);
    LOAD(PFN_vkDestroyDevice, vkDestroyDevice);
    LOAD(PFN_vkDestroyInstance, vkDestroyInstance);
    if (!vkEnumeratePhysicalDevices || !vkGetPhysicalDeviceProperties || !vkGetPhysicalDeviceQueueFamilyProperties || !vkEnumerateDeviceExtensionProperties || !vkCreateDevice || !vkDestroyDevice || !vkDestroyInstance)
        return failure("32-bit Vulkan loader is missing required entry points.");
    uint32_t count = 0;
    result = vkEnumeratePhysicalDevices(instance, &count, NULL);
    if (result != VK_SUCCESS || !count || count > 128) { vkDestroyInstance(instance, NULL); return failure("No 32-bit Vulkan devices could be enumerated."); }
    VkPhysicalDevice devices[128];
    result = vkEnumeratePhysicalDevices(instance, &count, devices);
    if (result != VK_SUCCESS) { vkDestroyInstance(instance, NULL); return failure("32-bit Vulkan device enumeration failed."); }
    printf("{\"format\":1,\"bits\":32,\"devices\":[");
    int usable_count = 0;
    for (uint32_t i = 0; i < count; ++i) {
        VkPhysicalDeviceProperties props; vkGetPhysicalDeviceProperties(devices[i], &props);
        char reason[160] = ""; int usable = 0;
        if (props.apiVersion < VK_API_VERSION_1_1) strcpy(reason, "GPU driver exposes Vulkan older than 1.1.");
        else {
            uint32_t queues = 0, queue = UINT32_MAX; vkGetPhysicalDeviceQueueFamilyProperties(devices[i], &queues, NULL);
            VkQueueFamilyProperties *families = queues && queues <= 1024 ? calloc(queues, sizeof(*families)) : NULL;
            if (families) {
                vkGetPhysicalDeviceQueueFamilyProperties(devices[i], &queues, families);
                for (uint32_t j = 0; j < queues; ++j) if (families[j].queueCount && (families[j].queueFlags & VK_QUEUE_GRAPHICS_BIT)) { queue = j; break; }
                free(families);
            }
            uint32_t extensions = 0; int swapchain = 0;
            result = vkEnumerateDeviceExtensionProperties(devices[i], NULL, &extensions, NULL);
            VkExtensionProperties *ext = result == VK_SUCCESS && extensions && extensions <= 4096 ? calloc(extensions, sizeof(*ext)) : NULL;
            if (ext) {
                if (vkEnumerateDeviceExtensionProperties(devices[i], NULL, &extensions, ext) == VK_SUCCESS)
                    for (uint32_t j = 0; j < extensions; ++j) if (!strcmp(ext[j].extensionName, VK_KHR_SWAPCHAIN_EXTENSION_NAME)) swapchain = 1;
                free(ext);
            }
            if (queue == UINT32_MAX) strcpy(reason, "No Vulkan graphics queue is available.");
            else if (!swapchain) strcpy(reason, "Driver does not expose VK_KHR_swapchain.");
            else {
                float priority = 1; const char *extension = VK_KHR_SWAPCHAIN_EXTENSION_NAME;
                VkDeviceQueueCreateInfo q = {.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO, .queueFamilyIndex = queue, .queueCount = 1, .pQueuePriorities = &priority};
                VkDeviceCreateInfo d = {.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO, .queueCreateInfoCount = 1, .pQueueCreateInfos = &q, .enabledExtensionCount = 1, .ppEnabledExtensionNames = &extension};
                VkDevice device;
                result = vkCreateDevice(devices[i], &d, NULL, &device);
                if (result == VK_SUCCESS) { usable = 1; ++usable_count; vkDestroyDevice(device, NULL); }
                else snprintf(reason, sizeof(reason), "32-bit vkCreateDevice failed (VkResult %d).", result);
            }
        }
        if (i) putchar(',');
        printf("{\"name\":"); json_string(props.deviceName);
        printf(",\"vendor\":%u,\"device\":%u,\"api\":\"%u.%u.%u\",\"usable\":%s,\"reason\":", props.vendorID, props.deviceID, VK_VERSION_MAJOR(props.apiVersion), VK_VERSION_MINOR(props.apiVersion), VK_VERSION_PATCH(props.apiVersion), usable ? "true" : "false");
        json_string(reason); putchar('}');
    }
    puts("]}"); vkDestroyInstance(instance, NULL); dlclose(library);
    return usable_count ? 0 : 2;
}
