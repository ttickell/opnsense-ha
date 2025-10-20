# How to Debug OPNsense Integration Issues

This guide documents lessons learned from debugging the `configctl` command syntax issue and establishes best practices for future OPNsense development work.

## The Case Study: configctl Command Format Issue

### The Problem
- Commands like `configctl interface linkup.start igc1` failed with "Action not allowed or missing"
- Initial assumption: Authentication or permission problems
- **Actual issue**: Wrong command syntax format

### The Solution
- **Correct**: `configctl interface linkup start igc1` (spaces)
- **Wrong**: `configctl interface linkup.start igc1` (dots)

### Time Investment Analysis
- **Total Debug Time**: ~3 hours
- **Root Cause Discovery**: Final 15 minutes  
- **Wasted Effort**: Authentication, process debugging, complex diagnostic scripts
- **What Should Have Been Done First**: Basic syntax validation (5 minutes)

## Debug Protocol for OPNsense Issues

### � **CRITICAL REMINDER: DOCUMENTATION FIRST!**

**Before any debugging, investigation, or coding:**

```bash
# ALWAYS start here - no exceptions!
configctl help                    # What commands exist?
man configctl                     # Manual pages
configctl <command> help          # Command-specific help
```

**If the user says "check the documentation" or "look at the source code" - STOP everything else and do that immediately.**

### �🚨 **ALWAYS START HERE - The 5-Minute Rule**

Before writing any diagnostic scripts or investigating complex issues:

```bash
# 1. Test the basic command manually
configctl help
configctl actions | grep interface

# 2. Validate syntax with working examples
configctl interface           # Does base command work?
configctl interface help      # What's the expected syntax?

# 3. Test minimal cases
configctl interface linkup start <interface>   # Test actual syntax
configctl interface linkup.start <interface>   # Test assumed syntax
```

**If the problem persists after 5 minutes of basic testing, THEN proceed to advanced debugging.**

### 📚 **Documentation Research Order**

1. **Built-in Help First**
   ```bash
   configctl help
   configctl <command> help
   man configctl
   ```

2. **OPNsense Source Code**
   ```bash
   # Check action definitions
   find /usr/local/opnsense/service/conf/actions.d/ -name "*.conf" | xargs grep -l interface
   
   # Look for working examples in OPNsense codebase
   grep -r "configctl interface" /usr/local/opnsense/
   ```

3. **Official Documentation**
   - OPNsense Developer Documentation
   - API Reference Guides
   - Community Forums (but verify with source)

### 🔍 **Systematic Debugging Steps**

If basic validation doesn't resolve the issue:

#### Step 1: Isolate the Problem
```bash
# Test each component separately
which configctl                    # Is command available?
configctl                         # Does it start?
configctl actions                 # Are actions loaded?
configctl <specific-action>       # Does target action exist?
```

#### Step 2: Check Service Status
```bash
# Only if Step 1 suggests service issues
service configd status
tail -f /var/log/configd.log
```

#### Step 3: Validate Permissions
```bash
# Only if commands work as root but fail as user
ls -la /var/run/configd.socket
whoami
groups
```

#### Step 4: Deep Source Analysis
Only if the above steps don't identify the issue:
- Examine configd source code
- Create targeted diagnostic scripts
- Test socket communication directly

### ⚠️ **Common Anti-Patterns to Avoid**

1. **Assumption-Based Development**
   ```bash
   # DON'T: Assume syntax without testing
   configctl interface.something.action
   
   # DO: Validate syntax first
   configctl help | grep interface
   ```

2. **Complex Before Simple**
   ```bash
   # DON'T: Start with elaborate diagnostic scripts
   #!/bin/sh
   # 200-line socket debugging script...
   
   # DO: Start with manual command testing
   configctl interface linkup start igc1
   ```

3. **Workaround Over Root Cause**
   ```bash
   # DON'T: Ship workarounds without understanding why
   if ! configctl interface.linkup.start; then
       /usr/local/etc/rc.linkup start  # Workaround
   fi
   
   # DO: Fix the real issue
   if ! configctl interface linkup start; then  # Correct syntax
       ifconfig "${interface}" up     # Fallback only
   fi
   ```

## Debugging Toolkit

### Quick Command Reference
```bash
# Essential OPNsense debugging commands
configctl help                           # List all available commands
configctl actions                        # Show loaded actions
service configd status                   # Check configd service
tail -f /var/log/configd.log            # Monitor configd logs
find /usr/local/opnsense -name "*.py" | xargs grep -l configctl  # Find examples
```

### Template for Minimal Test Scripts
```bash
#!/bin/sh
# Minimal test template - use before building complex solutions

COMMAND="configctl interface linkup start"
INTERFACE="igc1"

echo "Testing: ${COMMAND} ${INTERFACE}"
if ${COMMAND} ${INTERFACE}; then
    echo "SUCCESS: Command worked"
else
    echo "FAILED: Exit code $?"
    echo "Checking alternative syntax..."
    # Test variations here
fi
```

### Error Message Investigation
```bash
# When you get cryptic errors, check:
dmesg | tail -20                    # System messages
tail -20 /var/log/system.log       # System log
tail -20 /var/log/configd.log      # configd specific
ps aux | grep configd              # Process status
```

## Best Practices for Feature Development

### 1. Validation-Driven Development
```bash
# Before implementing new configctl integration:
# 1. Manually verify commands work
# 2. Check syntax in OPNsense source
# 3. Test error conditions
# 4. THEN implement in scripts
```

### 2. Progressive Error Handling
```bash
# Good error handling with context
if ! configctl interface linkup start "${interface}" 2>/dev/null; then
    logger -t ha-script "configctl failed for ${interface} - syntax: configctl interface linkup start <interface>"
    logger -t ha-script "Falling back to ifconfig method"
    ifconfig "${interface}" up
fi
```

### 3. Documentation of Assumptions
```bash
# Document WHY you're using specific syntax
# Use configctl with correct syntax (spaces not dots)
# Reference: /usr/local/opnsense/service/conf/actions.d/actions_interface.conf
# Format: configctl interface linkup start <interface>
configctl interface linkup start "${interface}"
```

## Time Management

### Escalation Timeline
- **0-5 minutes**: Manual command testing and basic validation
- **5-15 minutes**: Documentation research and syntax verification  
- **15-30 minutes**: Service status and permission checking
- **30+ minutes**: Deep debugging with custom scripts

### When to Stop and Ask for Help
- After 1 hour without identifying root cause
- When assumptions about OPNsense internals need validation
- If considering workarounds instead of fixes

## Lessons from the configctl Case

### What Worked Well
✅ **Persistence in finding root cause** rather than accepting workarounds  
✅ **Systematic creation of diagnostic tools** that isolated the problem  
✅ **Deep source code investigation** that revealed system architecture  
✅ **User-driven testing** that found the breakthrough  

### What Could Have Been Better
❌ **Started with complex solutions** instead of simple syntax testing  
❌ **Made assumptions about API format** without validation  
❌ **Spent hours on authentication** when the issue was syntax  
❌ **Built diagnostic scripts** before checking documentation  
❌ **Did not start with documentation research** despite user guidance to do so

### Critical Learning
**The user had to explicitly remind me to check documentation and source code** - this should have been the very first step, not a fallback after complex debugging failed.

### Key Insight
**The most complex-seeming problems often have simple root causes.** Always validate basic assumptions first.

## Quick Reference Checklist

Before diving into complex debugging:

- [ ] Can I run the command manually?
- [ ] Have I checked the built-in help?
- [ ] Did I verify the syntax format?
- [ ] Are there working examples in OPNsense source?
- [ ] Have I tested the simplest possible case?

**Only after answering "yes" to all above should you create diagnostic scripts or investigate complex system issues.**

---

*Remember: The goal is not just to solve the immediate problem, but to understand the system well enough to avoid similar issues in the future.*