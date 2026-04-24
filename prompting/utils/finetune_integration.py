# #!/usr/bin/env python3
# """
# Integration script for fine-tuning pipeline - updated to use pre-created files.
# This is now a thin wrapper around the updated MeteorologyFineTuner.
# """

# from pathlib import Path
# import json
# import os
# from typing import Dict

# # Import the updated fine-tuner
# from prompting.utils.llama_finetuning_pipeline import MeteorologyFineTuner

# def check_required_files():
#     """Check if required data files exist."""
    
#     required_files = {
#         "train_data.json": "Training data (run: python generate_training_data.py)",
#         "test_data.json": "Few-shot testing data (run: python create_train_test_datasets.py)",
#         "test_data_zero_shot.json": "Zero-shot testing data (run: python create_zero_shot_test_dataset.py)"
#     }
    
#     missing_files = []
#     available_files = []
    
#     for file, description in required_files.items():
#         if Path(file).exists():
#             available_files.append(file)
#             print(f"✅ Found: {file}")
#         else:
#             missing_files.append((file, description))
#             print(f"❌ Missing: {file} - {description}")
    
#     return available_files, missing_files

# def run_finetuning_pipeline(args):
#     """Run the complete fine-tuning pipeline using pre-created files."""
    
#     print("=" * 80)
#     print("LLAMA 3.1 8B FINE-TUNING PIPELINE (FILE-BASED APPROACH)")
#     print("=" * 80)
    
#     # Check required files
#     print("📋 CHECKING REQUIRED FILES:")
#     available_files, missing_files = check_required_files()
    
#     # Determine zero_shot from args
#     zero_shot = getattr(args, 'zero_shot', False)
    
#     # Determine what can be done based on available files
#     can_train = "train_data.json" in available_files
#     can_test_fewshot = "test_data.json" in available_files
#     can_test_zeroshot = "test_data_zero_shot.json" in available_files
    
#     print(f"\n📊 CAPABILITIES BASED ON AVAILABLE FILES:")
#     print(f"   Training: {'✅ Available' if can_train else '❌ Missing train_data.json'}")
#     print(f"   Few-shot testing: {'✅ Available' if can_test_fewshot else '❌ Missing test_data.json'}")
#     print(f"   Zero-shot testing: {'✅ Available' if can_test_zeroshot else '❌ Missing test_data_zero_shot.json'}")
    
#     # Check if we can proceed
#     if not args.skip_training and not can_train:
#         print(f"\n❌ Cannot train without train_data.json")
#         print(f"   Run: python generate_training_data.py")
#         return False
    
#     if not args.skip_testing:
#         if zero_shot and not can_test_zeroshot:
#             print(f"\n❌ Cannot do zero-shot testing without test_data_zero_shot.json")
#             print(f"   Run: python create_zero_shot_test_dataset.py")
#             return False
#         elif not zero_shot and not can_test_fewshot:
#             print(f"\n❌ Cannot do few-shot testing without test_data.json")
#             print(f"   Run: python create_train_test_datasets.py")
#             return False
    
#     # Initialize fine-tuner
#     print(f"\n🔧 INITIALIZING FINE-TUNER:")
#     fine_tuner = MeteorologyFineTuner(output_dir="fine_tuned_llm")
    
#     # Determine testing approach
#     if zero_shot:
#         approach = "zero-shot"
#         print(f"   Using zero-shot approach")
#     else:
#         approach = "few-shot"
#         print(f"   Using few-shot approach")
    
#     print(f"   Skip training: {args.skip_training}")
#     print(f"   Skip testing: {args.skip_testing}")
    
#     try:
#         # Run the complete pipeline
#         success = fine_tuner.run_complete_pipeline(
#             year=args.year,
#             past_days=args.past_days,
#             batch_size=args.batch_size,
#             skip_training=args.skip_training,
#             skip_testing=args.skip_testing,
#             zero_shot=zero_shot
#         )
        
#         if success:
#             print(f"\n🎉 PIPELINE COMPLETED SUCCESSFULLY!")
#             print(f"   Results saved in 'fine_tuned_llm' folder")
            
#             # Show what was created
#             if not args.skip_training:
#                 print(f"   📁 Model: fine_tuned_llm/model/final_model/")
            
#             if not args.skip_testing:
#                 print(f"   📁 Responses ({approach}): fine_tuned_llm/responses/{approach}/")
#                 print(f"   📁 Analysis: fine_tuned_llm/results/{approach}/")
            
#         return success
        
#     except Exception as e:
#         print(f"\n❌ Pipeline failed with error: {str(e)}")
#         return False

# def run_comparison_pipeline(args):
#     """Run both few-shot and zero-shot approaches for comparison."""
    
#     print("=" * 80)
#     print("COMPARISON PIPELINE (FEW-SHOT vs ZERO-SHOT)")
#     print("=" * 80)
    
#     # Check if both datasets exist
#     available_files, missing_files = check_required_files()
    
#     if "test_data.json" not in available_files:
#         print(f"❌ Missing few-shot data: test_data.json")
#         return False
    
#     if "test_data_zero_shot.json" not in available_files:
#         print(f"❌ Missing zero-shot data: test_data_zero_shot.json")
#         return False
    
#     # Initialize fine-tuner
#     fine_tuner = MeteorologyFineTuner(output_dir="fine_tuned_llm")
    
#     try:
#         # Run comparison
#         fine_tuner.compare_approaches(past_days=args.past_days)
        
#         print(f"\n🎉 COMPARISON COMPLETED!")
#         print(f"   Check results folders for performance comparison:")
#         print(f"   📁 Few-shot: fine_tuned_llm/results/few-shot/")
#         print(f"   📁 Zero-shot: fine_tuned_llm/results/zero-shot/")
#         return True
        
#     except Exception as e:
#         print(f"\n❌ Comparison failed with error: {str(e)}")
#         return False

# def validate_pipeline_setup():
#     """Validate that the pipeline setup is correct."""
    
#     print("🔍 VALIDATING PIPELINE SETUP:")
    
#     # Check if core classes can be imported
#     try:
#         from prompting.utils.llama_finetuning_pipeline import MeteorologyFineTuner
#         print("✅ MeteorologyFineTuner imported successfully")
#     except ImportError as e:
#         print(f"❌ Cannot import MeteorologyFineTuner: {e}")
#         return False
    
#     # Check if data files exist and are valid
#     available_files, missing_files = check_required_files()
    
#     # Validate file formats
#     for file in available_files:
#         try:
#             with open(file, 'r', encoding='utf-8') as f:
#                 data = json.load(f)
            
#             if file == "train_data.json":
#                 if data and 'messages' in data[0]:
#                     print(f"✅ {file} format is valid (messages)")
#                 else:
#                     print(f"❌ {file} format is invalid")
#                     return False
            
#             elif file in ["test_data.json", "test_data_zero_shot.json"]:
#                 if data and 'system_prompt' in data[0] and 'user_prompt' in data[0]:
#                     print(f"✅ {file} format is valid (prompts)")
#                 else:
#                     print(f"❌ {file} format is invalid")
#                     return False
            
#         except Exception as e:
#             print(f"❌ Error validating {file}: {e}")
#             return False
    
#     print("✅ Pipeline setup validation passed!")
#     return True

# def show_usage_examples():
#     """Show usage examples for the pipeline."""
    
#     print("\n" + "=" * 60)
#     print("USAGE EXAMPLES")
#     print("=" * 60)
#     print("1. Complete pipeline (training + few-shot testing):")
#     print("   python main.py --finetune --year 2024 --past_days 5")
#     print()
#     print("2. Complete pipeline (training + zero-shot testing):")
#     print("   python main.py --finetune --year 2024 --past_days 5 --zero_shot")
#     print()
#     print("3. Only training:")
#     print("   python main.py --finetune --year 2024 --skip_testing")
#     print()
#     print("4. Only few-shot testing (model already trained):")
#     print("   python main.py --finetune --year 2024 --skip_training")
#     print()
#     print("5. Only zero-shot testing (model already trained):")
#     print("   python main.py --finetune --year 2024 --skip_training --zero_shot")
#     print()
#     print("6. Compare both approaches:")
#     print("   python main.py --finetune --year 2024 --skip_training --compare")
#     print()
#     print("Required files:")
#     print("   - train_data.json (for training)")
#     print("   - test_data.json (for few-shot testing)")
#     print("   - test_data_zero_shot.json (for zero-shot testing)")
#     print("=" * 60)

# if __name__ == "__main__":
#     # When run directly, show validation and usage
#     validate_pipeline_setup()
#     show_usage_examples()

#!/usr/bin/env python3
"""
Integration layer between main.py and the fine-tuning pipeline.

Thin wrapper that validates required data files exist, constructs the
MeteorologyFineTuner, and delegates to either run_complete_pipeline or
run_both_approaches depending on the CLI flags. Also exposes two
standalone dev tools (validate_pipeline_setup, show_usage_examples)
that run when this file is executed directly.

Called from main.py via run_finetuning_pipeline(args) and
run_comparison_pipeline(args).
"""

import json
from pathlib import Path

from prompting.utils.finetuning_pipeline import MeteorologyFineTuner


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REQUIRED_FILES = {
    "train_data.json": {
        "description": "Training data",
        "generator": "generate_training_data.py",
    },
    "test_data.json": {
        "description": "Few-shot testing data",
        "generator": "create_train_test_datasets.py",
    },
    "test_data_zero_shot.json": {
        "description": "Zero-shot testing data",
        "generator": "create_zero_shot_test_dataset.py",
    },
}


# ---------------------------------------------------------------------------
# File-availability helpers
# ---------------------------------------------------------------------------

def check_required_files():
    """
    Check which of the expected input files are present.

    Returns:
        (available_files, missing_files) tuple. available_files is a list
        of filenames. missing_files is a list of (filename, description,
        generator_script) tuples.
    """
    available_files = []
    missing_files = []

    for filename, info in _REQUIRED_FILES.items():
        if Path(filename).exists():
            available_files.append(filename)
            print(f"Found: {filename}")
        else:
            missing_files.append((filename, info["description"], info["generator"]))
            print(
                f"MISSING: {filename} ({info['description']} - "
                f"run: python {info['generator']})"
            )

    return available_files, missing_files


# ---------------------------------------------------------------------------
# Pipeline orchestration
# ---------------------------------------------------------------------------

def run_finetuning_pipeline(args):
    """
    Run the complete fine-tuning pipeline using pre-created data files.

    Expects args to have: skip_training, skip_testing, past_days,
    batch_size, and optionally zero_shot.

    Returns True on success, False on any early exit (missing files,
    incompatible flags, exceptions).
    """
    print("Fine-tuning pipeline (file-based approach)")

    zero_shot = getattr(args, "zero_shot", False)
    approach = "zero-shot" if zero_shot else "few-shot"

    available_files, _ = check_required_files()

    can_train = "train_data.json" in available_files
    can_test_fewshot = "test_data.json" in available_files
    can_test_zeroshot = "test_data_zero_shot.json" in available_files

    print(f"Training available: {can_train}")
    print(f"Few-shot testing available: {can_test_fewshot}")
    print(f"Zero-shot testing available: {can_test_zeroshot}")

    # Hard fail early if the user's flags demand a file that isn't there
    if not args.skip_training and not can_train:
        print(
            "ERROR: cannot train without train_data.json. "
            "Run: python generate_training_data.py"
        )
        return False

    if not args.skip_testing:
        if zero_shot and not can_test_zeroshot:
            print(
                "ERROR: cannot do zero-shot testing without test_data_zero_shot.json. "
                "Run: python create_zero_shot_test_dataset.py"
            )
            return False
        if not zero_shot and not can_test_fewshot:
            print(
                "ERROR: cannot do few-shot testing without test_data.json. "
                "Run: python create_train_test_datasets.py"
            )
            return False

    fine_tuner = MeteorologyFineTuner(
        output_dir="fine_tuned_llm",
        training_seed=getattr(args, "training_seed", 42),
        use_completion_only_collator=not getattr(args, "legacy_collator", False),
    )
    print(
        f"Fine-tuner initialized: approach={approach}, "
        f"skip_training={args.skip_training}, skip_testing={args.skip_testing}"
    )

    try:
        success = fine_tuner.run_complete_pipeline(
            year=args.year,
            past_days=args.past_days,
            batch_size=args.batch_size,
            skip_training=args.skip_training,
            skip_testing=args.skip_testing,
            zero_shot=zero_shot,
            n_seeds=getattr(args, "n_seeds", 1),
            num_predict=getattr(args, "num_predict", 512),
            num_ctx=getattr(args, "num_ctx", 16384),
        )
    except Exception as e:
        print(f"ERROR: pipeline failed: {e}")
        return False

    if not success:
        return False

    print("Pipeline completed; results saved to 'fine_tuned_llm/'")
    if not args.skip_training:
        print("  Model: fine_tuned_llm/model/final_model/")
    if not args.skip_testing:
        print(f"  Responses: fine_tuned_llm/responses/{approach}/")
        print(f"  Analysis: fine_tuned_llm/results/{approach}/")
    return True


def run_comparison_pipeline(args):
    """
    Run both few-shot and zero-shot testing + evaluation against an
    already-trained model. Produces results in separate folders for
    manual side-by-side comparison; does not synthesize a diff.

    Expects args to have: past_days.

    Returns True on success, False on any early exit.
    """
    print("Running both approaches (few-shot and zero-shot)")

    available_files, _ = check_required_files()

    if "test_data.json" not in available_files:
        print("ERROR: missing few-shot data (test_data.json)")
        return False
    if "test_data_zero_shot.json" not in available_files:
        print("ERROR: missing zero-shot data (test_data_zero_shot.json)")
        return False

    fine_tuner = MeteorologyFineTuner(
        output_dir="fine_tuned_llm",
        training_seed=getattr(args, "training_seed", 42),
        use_completion_only_collator=not getattr(args, "legacy_collator", False),
    )

    try:
        # Renamed from compare_approaches in the cleaned pipeline; the
        # method runs both flavors but does not synthesize a comparison
        # between them - check the per-approach results folders manually.
        fine_tuner.run_both_approaches(
            past_days=args.past_days,
            n_seeds=getattr(args, "n_seeds", 1),
        )
    except Exception as e:
        print(f"ERROR: comparison failed: {e}")
        return False

    print("Both approaches complete")
    print("  Few-shot results: fine_tuned_llm/results/few-shot/")
    print("  Zero-shot results: fine_tuned_llm/results/zero-shot/")
    return True


# ---------------------------------------------------------------------------
# Standalone dev tools (run when this file is executed directly)
# ---------------------------------------------------------------------------

def validate_pipeline_setup():
    """
    Validate that imports work and data files are present + well-formed.
    Standalone diagnostic; not invoked from main.py.
    """
    print("Validating pipeline setup")

    # Check that the fine-tuner imports cleanly
    try:
        from prompting.utils.finetuning_pipeline import MeteorologyFineTuner  # noqa: F401
        print("MeteorologyFineTuner imported successfully")
    except ImportError as e:
        print(f"ERROR: cannot import MeteorologyFineTuner: {e}")
        return False

    available_files, _ = check_required_files()

    # Shallow format validation on each available file. MeteorologyFineTuner
    # will do per-example validation at load time, so we only check that
    # the file is parseable JSON and the top-level shape looks right.
    for filename in available_files:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"ERROR: cannot parse {filename}: {e}")
            return False

        if not data:
            print(f"ERROR: {filename} is empty")
            return False

        first_item = data[0]
        if filename == "train_data.json":
            if "messages" not in first_item:
                print(f"ERROR: {filename} first item has no 'messages' key")
                return False
            print(f"{filename} format looks valid (messages schema)")
        elif filename in ("test_data.json", "test_data_zero_shot.json"):
            if "system_prompt" not in first_item or "user_prompt" not in first_item:
                print(
                    f"ERROR: {filename} first item missing system_prompt or user_prompt"
                )
                return False
            print(f"{filename} format looks valid (prompts schema)")

    print("Pipeline setup validation passed")
    return True


def show_usage_examples():
    """Print common command-line invocations for the fine-tuning pipeline."""
    print("Usage examples:")
    print("  Complete pipeline (training + few-shot testing):")
    print("    python main.py --finetune --year 2024 --past_days 4")
    print()
    print("  Complete pipeline (training + zero-shot testing):")
    print("    python main.py --finetune --year 2024 --past_days 4 --zero_shot")
    print()
    print("  Training only:")
    print("    python main.py --finetune --year 2024 --skip_testing")
    print()
    print("  Testing only (few-shot), model already trained:")
    print("    python main.py --finetune --year 2024 --skip_training")
    print()
    print("  Testing only (zero-shot), model already trained:")
    print("    python main.py --finetune --year 2024 --skip_training --zero_shot")
    print()
    print("  Compare both approaches (testing + evaluation for each):")
    print("    python main.py --finetune --year 2024 --skip_training --compare")
    print()
    print("Required files:")
    print("  train_data.json                (for training)")
    print("  test_data.json                 (for few-shot testing)")
    print("  test_data_zero_shot.json       (for zero-shot testing)")


if __name__ == "__main__":
    validate_pipeline_setup()
    show_usage_examples()
    
